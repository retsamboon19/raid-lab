"""Copy only the observed bootstrap catalog inputs into the scratch patch root."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[3]
SANDBOX = ROOT / 'tools/raid-lab/private/native-player-20261008a'
SOURCE = ROOT / 'NIKKE/Unity/com_proximabeta_NIKKE/com.shiftup.patch/core'
TARGET = SANDBOX / 'profile/AppData/LocalLow/com_proximabeta/NIKKE/com.shiftup.patch/core'
paths = ('catalog.ndb', 'catalog.ndb.nds', 'raw/5256e42159f92f5671525298beb80762.db',
         'raw/734b5377049c8a5ac4075caf1357343b.nds')
rows = []
for relative in paths:
    source, target = SOURCE / relative, TARGET / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise RuntimeError('Do not overwrite staged catalog evidence: '+str(target))
    shutil.copy2(source, target)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    assert hashlib.sha256(target.read_bytes()).hexdigest() == digest
    rows.append(dict(source=str(source),copy=str(target),sha256=digest))
source = ROOT / 'tools/raid-lab/private/native-current-tables-2df7134a.zip'
target = SANDBOX / 'current-tables.zip'
shutil.copy2(source, target)
digest = hashlib.sha256(source.read_bytes()).hexdigest()
assert hashlib.sha256(target.read_bytes()).hexdigest() == digest
rows.append(dict(source=str(source),copy=str(target),sha256=digest))
(SANDBOX / 'bootstrap-resources.json').write_text(json.dumps(rows,indent=2))
print(json.dumps({'copied':len(rows)}))
