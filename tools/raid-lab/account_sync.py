"""Fresh BlaBlaLink reads; complete snapshots replace saved investment atomically."""
import hashlib
import json
import os
from pathlib import Path
import secrets
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parent
PRIVATE=ROOT/'private'

class LoginRequired(Exception):pass
class RefreshError(Exception):pass
class AccountSelectionRequired(RefreshError):pass

def atomic_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.'+secrets.token_hex(4)+'.tmp')
    temporary.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
    os.replace(temporary,path)

def fetch_latest(cookie,post,progress=lambda **kw:None,preferred_area=None,account_id=None):
    """Do not reuse old character/build/research fields on any failed response."""
    from http.cookies import SimpleCookie
    if account_id is None:
        jar=SimpleCookie();jar.load(cookie)
        if 'game_token' not in jar or 'game_openid' not in jar:raise LoginRequired()
        openid=jar['game_openid'].value
    else:openid=str(account_id)
    def request(route,body,discover=False):
        try:response=post(route,body,cookie)
        except InterruptedError:raise
        except Exception:raise RefreshError('Could not reach BlaBlaLink. Your saved roster was not changed.') from None
        if response.get('code') in (300001,401):raise LoginRequired('BlaBlaLink rejected the saved session.')
        if response.get('code')==403:raise RefreshError('BlaBlaLink denied the data request (403). Signing in again may not resolve this.')
        if discover and response.get('code')!=0:return {}
        if response.get('code')!=0:raise RefreshError('BlaBlaLink rejected the account refresh. Your saved roster was not changed.')
        data=response.get('data')
        if not isinstance(data,dict):raise RefreshError('BlaBlaLink returned an incomplete response.')
        return data
    areas=[preferred_area] if preferred_area else [83,1,261,219,145,81,82,85]
    roster=None;area=None
    for candidate in areas:
        progress(phase='Reading your BlaBlaLink roster')
        data=request('Game/GetUserCharacters',{'intl_open_id':openid,'nikke_area_id':candidate},discover=True)
        if data.get('characters'):roster=data;area=candidate;break
    if roster is None:raise AccountSelectionRequired('BlaBlaLink returned no roster for the selected account and server.')
    codes=[c['name_code'] for c in roster['characters']]
    if len(codes)!=len(set(codes)) or not codes:raise RefreshError('BlaBlaLink returned an invalid character list.')
    details=[]
    for start in range(0,len(codes),60):
        progress(phase=f'Reading gear, skills and cubes · {min(start+60,len(codes))}/{len(codes)} units')
        details.append(request('Game/GetUserCharacterDetails',{'intl_open_id':openid,'nikke_area_id':area,'name_codes':codes[start:start+60]}))
    received={str(r['name_code']) for batch in details for r in batch.get('character_details',[])}
    if received!={str(c) for c in codes}:raise RefreshError('Some character details were missing. Your saved roster was not changed.')
    progress(phase='Reading research and synchro levels')
    outpost=request('Game/GetUserProfileOutpostInfo',{'intl_open_id':openid,'nikke_area_id':area})
    if not outpost.get('outpost_info',{}).get('recycle_room_researches'):
        raise RefreshError('Research data was missing. Your saved roster was not changed.')
    snapshot={'format':'nikke-offline-blablalink-v1','complete':True,'missing_codes':[],'errors':[],
              'captured_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
              'roster':roster,'details':details,'outpost':outpost}
    return snapshot,{'area':area,'account_hash':hashlib.sha256(openid.encode()).hexdigest()}

def convert_and_save(snapshot,previous_path=None):
    import core
    path=previous_path or PRIVATE/'roster.json'
    fresh=core.import_roster(snapshot)
    # Preserve search inclusion choices; all live investment comes from the API.
    if path.exists():
        old=core.read(path)
        enabled={r['id']:r.get('enabled',True) for r in old.get('roster',[])}
        for row in fresh['roster']:row['enabled']=enabled.get(row['id'],True)
    fresh['refreshed_at']=snapshot['captured_at']
    fresh['source']='BlaBlaLink · refreshed '+snapshot['captured_at']
    atomic_json(path,fresh)
    return fresh
