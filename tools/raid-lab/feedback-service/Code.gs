/* Private Drive inbox. Deploy as owner; never grant submitters folder access. */
function validateFeedback(body) {
  const fields=['id','message','profile_url','recommendation','owned_units','ownership_basis','squad','image'];
  if(!body || Object.keys(body).sort().join()!==fields.sort().join()) throw Error('Invalid feedback fields.');
  if(!/^[a-f0-9]{32}$/.test(body.id)) throw Error('Invalid submission ID.');
  if(typeof body.message!=='string'||body.message.trim().length<5||body.message.length>2000) throw Error('Write 5–2,000 characters of feedback.');
  if(typeof body.profile_url!=='string'||!/^https:\/\/(www\.)?blablalink\.com\/shiftyspad\?uid=[A-Za-z0-9%_=-]{1,300}$/.test(body.profile_url)) throw Error('A BlaBlaLink shared profile link is required.');
  if(!body.recommendation||!Array.isArray(body.recommendation.teams)||body.recommendation.teams.length<1||body.recommendation.teams.length>5) throw Error('A recommendation is required.');
  if(!Number.isInteger(body.squad)||body.squad<0||body.squad>=body.recommendation.teams.length) throw Error('Invalid squad.');
  if(!Array.isArray(body.owned_units)||body.owned_units.length<1||body.owned_units.length>1000) throw Error('Owned units are required.');
  if(!['recommendation-time','current-roster; historical ownership unavailable'].includes(body.ownership_basis)) throw Error('Invalid ownership label.');
  const image=body.image;
  if(!image||Object.keys(image).sort().join()!=='data,type'||typeof image.data!=='string'||image.data.length>2666668||!image.data.length||!/^([A-Za-z0-9+/]{4})*([A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(image.data)) throw Error('Attach one PNG or JPEG up to 2 MB.');
  const bytes=Utilities.base64Decode(image.data), unsigned=bytes.map(x=>(x+256)%256);
  const png=image.type==='image/png'&&[137,80,78,71,13,10,26,10].every((x,i)=>unsigned[i]===x);
  const jpeg=image.type==='image/jpeg'&&unsigned[0]===255&&unsigned[1]===216&&unsigned[2]===255&&unsigned.at(-2)===255&&unsigned.at(-1)===217;
  if(bytes.length>2000000||(!png&&!jpeg)) throw Error('Only PNG and JPEG images are accepted.');
  const metadata={...body};delete metadata.image;
  if(JSON.stringify(metadata).length>900000) throw Error('Feedback details are too large.');
  return {metadata,bytes,extension:png?'png':'jpg'};
}

function doPost(event) {
  let lock;
  try {
    const text=event?.postData?.contents;
    if(typeof text!=='string'||text.length>4000000) throw Error('Feedback request is too large.');
    const body=JSON.parse(text), validated=validateFeedback(body);
    const folderId=PropertiesService.getScriptProperties().getProperty('FEEDBACK_FOLDER_ID');
    if(!folderId) throw Error('The feedback inbox has not been configured.');
    lock=LockService.getScriptLock();if(!lock.tryLock(10000)) throw Error('Inbox busy. Please retry.');
    const folder=DriveApp.getFolderById(folderId);
    if(folder.getSharingAccess()!==DriveApp.Access.PRIVATE) throw Error('The maintainer must restrict the feedback folder before accepting uploads.');
    // One ZIP is created atomically. Retries never create a half-filled submission.
    const name='feedback-'+body.id+'.zip';
    if(folder.getFilesByName(name).hasNext()) return reply({ok:true,id:body.id});
    const metadata={...validated.metadata,received_at:new Date().toISOString()};
    const readme='Raid Lab battle feedback\n\nSquad: '+(body.squad+1)+'\nProfile: '+body.profile_url+'\nOwnership snapshot: '+body.ownership_basis+'\n\n'+body.message+'\n\nSee feedback.json for the recommendation, builds, settings and owned units.\n';
    const files=[Utilities.newBlob(validated.bytes,body.image.type,'battle-record.'+validated.extension),Utilities.newBlob(JSON.stringify(metadata,null,2),'application/json','feedback.json'),Utilities.newBlob(readme,'text/plain','Read me.txt')];
    const savedFile=folder.createFile(Utilities.zip(files,name));
    // Notification failure must never reject feedback already stored in Drive.
    try {notifyFeedback(savedFile,body);} catch(error) {console.warn('Feedback saved, but email notification failed. Check email authorization and Google mail quota.');}
    return reply({ok:true,id:body.id});
  } catch(error) {
    // Do not expose Drive IDs, service errors or account information to clients.
    const message=String(error.message||'');
    const safe=/^(Invalid|Write |A recommendation|A BlaBlaLink|Owned units|Attach one|Only PNG|Feedback |The feedback inbox|The maintainer must|Inbox busy)/.test(message);
    return reply({ok:false,error:safe?message:'Upload was not confirmed. Retry using the same submission.'});
  } finally {if(lock&&lock.hasLock())lock.releaseLock();}
}
function reply(value){return ContentService.createTextOutput(JSON.stringify(value)).setMimeType(ContentService.MimeType.JSON);}
function doGet(){return reply({service:'Raid Lab private feedback',version:2});}

function notifyFeedback(file,body){
  const recipient=PropertiesService.getScriptProperties().getProperty('FEEDBACK_NOTIFY_EMAIL');
  if(!recipient)return;
  const settings=body.recommendation.settings||{};
  const boss=String(settings.encounter?.name||settings.boss_id||'Unspecified boss').replace(/[\r\n]/g,' ').slice(0,120);
  MailApp.sendEmail({to:recipient,subject:'Raid Lab: new battle feedback — '+boss,
    body:'New battle feedback received.\n\nBoss: '+boss+'\nMode: '+String(settings.content_mode||'Unspecified')+'\nSquad: '+(body.squad+1)+'\nReceipt: '+body.id+'\n\nOpen the private feedback ZIP:\n'+file.getUrl()+'\n\nThe screenshot, user message and roster details are inside. The file remains private.',name:'Raid Lab feedback'});
}

// Run in the editor once, then update the existing web-app deployment.
function enableEmailNotifications(){
  checkInbox();
  const recipient=Session.getEffectiveUser().getEmail();
  if(!recipient)throw Error('Google could not determine your email address. Run this from the script editor while signed in.');
  MailApp.sendEmail({to:recipient,subject:'Raid Lab feedback notifications — setup test',body:'Email delivery is working. Update your existing web-app deployment to a new version to activate notifications for new feedback.',name:'Raid Lab feedback'});
  PropertiesService.getScriptProperties().setProperty('FEEDBACK_NOTIFY_EMAIL',recipient);
  console.log('Notification recipient saved and setup email sent. Update the existing deployment to a new version.');
}

// Run once in the editor to authorize and check the private destination.
function checkInbox(){
  const id=PropertiesService.getScriptProperties().getProperty('FEEDBACK_FOLDER_ID');
  if(!id)throw Error('Set FEEDBACK_FOLDER_ID in Project Settings first.');
  const folder=DriveApp.getFolderById(id);
  if(folder.getSharingAccess()!==DriveApp.Access.PRIVATE)throw Error('Set General access to Restricted.');
  console.log('Private inbox is ready.');
}
