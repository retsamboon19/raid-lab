'use strict';
const RaidFeedback = (() => {
 const copy = value => JSON.parse(JSON.stringify(value));
 const pick = (obj, keys) => Object.fromEntries(keys.filter(k => obj?.[k] !== undefined).map(k => [k, copy(obj[k])]));
 function packageReport(report) {
  return { ...pick(report, ['history','kind','total','elapsed','simulations','settings','completion']), teams:report.teams.map(t => ({...pick(t,['members','builds','damage','dps','breakdown','damage_accounting','bursts','burst_log','critical_part_requirement','control_comparison']),fight:pick(t.encounter_timeline,['model','survival','simulated_until','off_burst_controller','control_plan','critical_deadlines','critical_parts','stop_reason'])})) };
 }
 function owned(roster) {return roster.map(r => pick(r, ['id','name','build','enabled','assumptions']));}
 function create({api, getRoster, getCatalog}) {
  const dialog = document.createElement('dialog'); dialog.id='feedbackDialog'; dialog.setAttribute('aria-labelledby','feedbackTitle');
  dialog.innerHTML=`<form><div class="dialog-title"><div><p class="eyebrow">HELP IMPROVE RECOMMENDATIONS</p><h2 id="feedbackTitle">Report your battle result</h2></div><button type="button" data-close class="quiet">Close</button></div><p>Did your in-game result differ? Send one Battle Records screenshot and tell us what happened.</p><label>Squad you tried<select name="squad"></select></label><label>Short feedback<textarea name="message" rows="4" minlength="5" maxlength="2000" required placeholder="What differed? Mention changes to the team, battle duration, who you controlled, and whether critical parts broke in time."></textarea></label><label>Battle Records image · PNG or JPEG, up to 2 MB<input name="image" type="file" accept="image/png,image/jpeg" required></label><img class="feedback-preview" alt="Your attached Battle Records" hidden><details><summary>See an example Battle Records screen</summary><p>After the battle, open Battle Records and capture all five units and the total battle time.</p><img class="feedback-example" src="/battle-record-example.png" alt="Example Battle Records showing five Nikke, individual damage and total battle time" loading="lazy"></details><label>Your BlaBlaLink shared profile link<input name="profile" type="url" required placeholder="https://www.blablalink.com/shiftyspad?uid=…"></label><small>Saved on this device for future feedback. Use your public ShiftyPad share link, not a login URL.</small><details><summary>What will be sent</summary><p data-context></p><p>Your message, image, profile link, recommendation with exact builds and encounter settings, and owned-unit snapshot go to the maintainer’s private feedback inbox. Login cookies and passwords are not included.</p><button type="button" data-download>Download attached details for review</button></details><p class="muted">Battle Records includes summon damage. The attached report preserves both boss and all-target damage when available.</p><p data-status role="status" aria-live="polite"></p><div class="dialog-actions"><button type="submit" class="primary">Send feedback</button></div></form>`;
  document.body.append(dialog);
  const form=dialog.querySelector('form'), el=name=>form.elements.namedItem(name), status=dialog.querySelector('[data-status]'), send=form.querySelector('[type=submit]');
  let snapshot, preview='', sending=false, sent=false, lastContent='';
  const close=()=>{if(!sending)dialog.close();};
  dialog.querySelector('[data-close]').onclick=close;
  dialog.addEventListener('cancel',e=>{if(sending)e.preventDefault();});
  dialog.addEventListener('close',()=>{if(preview)URL.revokeObjectURL(preview);});
  el('image').onchange=()=>{if(preview)URL.revokeObjectURL(preview);const file=el('image').files[0], img=dialog.querySelector('.feedback-preview');img.hidden=true;if(file&&file.size<=2000000&&['image/png','image/jpeg'].includes(file.type)){preview=URL.createObjectURL(file);img.src=preview;img.hidden=false;}else if(file){el('image').value='';status.textContent='Choose one PNG or JPEG no larger than 2 MB.';}};
  const details=()=>({...snapshot,squad:Number(el('squad').value),message:el('message').value.trim(),profile_url:el('profile').value.trim()});
  dialog.querySelector('[data-download]').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(details(),null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='raid-lab-feedback-details.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
  async function open(report, squad=0) {
   if(dialog.open)return;
   form.reset();sent=false;lastContent='';send.disabled=true;status.textContent='Checking feedback service…';dialog.querySelector('.feedback-preview').hidden=true;
   snapshot={id:crypto.randomUUID().replaceAll('-',''),recommendation:packageReport(report),owned_units:owned(report.feedback_context?.owned_units||getRoster()),ownership_basis:report.feedback_context?'recommendation-time':'current-roster; historical ownership unavailable'};
   const catalog=getCatalog();el('squad').replaceChildren(...report.teams.map((t,i)=>new Option(`Squad ${i+1} · ${t.members.map(id=>catalog[id]?.name||id).join(' / ')}`,i)));el('squad').value=String(squad);
   try{el('profile').value=localStorage.getItem('raid-lab-feedback-profile')||'';}catch{}
   dialog.querySelector('[data-context]').textContent=`${snapshot.owned_units.length} owned units · ${snapshot.ownership_basis==='recommendation-time'?'captured when this recommendation was generated':'current roster; this older recommendation did not record owned units'}. All ${report.teams.length} squads are included, with the squad you tried identified.`;
   dialog.showModal();
   try {
    const config=await api('feedback-config');if(!dialog.open)return;
    if(!config.enabled){status.textContent='The maintainer has not activated private feedback uploads yet. You can still prepare and download the details.';return;}
    send.disabled=false;status.textContent='Ready to send to the private feedback inbox.';
   }catch(error){status.textContent=error.message;}
  }
  form.onsubmit=async event=>{
   event.preventDefault();if(sending||sent)return;
   const file=el('image').files[0];if(!file||file.size>2000000)return;
   sending=true;send.disabled=true;dialog.querySelector('[data-close]').disabled=true;status.textContent='Sending feedback…';
   try {
    const data=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=()=>reject(Error('Could not read the image.'));reader.readAsDataURL(file);});
    const body={...details(),image:{type:file.type,data}};
    const content=JSON.stringify({...body,id:undefined});
    if(lastContent&&lastContent!==content){snapshot.id=crypto.randomUUID().replaceAll('-','');body.id=snapshot.id;}
    lastContent=content;
    await api('feedback',body);sent=true;status.textContent='Feedback received. Thank you — receipt '+snapshot.id+'.';
    try{localStorage.setItem('raid-lab-feedback-profile',body.profile_url);}catch{}
   }catch(error){status.textContent=error.message;send.disabled=false;}
   finally{sending=false;dialog.querySelector('[data-close]').disabled=false;}
  };
  return {open};
 }
 return {create,packageReport,owned};
})();
