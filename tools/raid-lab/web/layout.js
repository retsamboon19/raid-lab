// Collapsible workspace panels. Collapsed state is a per-browser convenience only.
(function(){
  const KEY='raidlab.collapsed';
  const load=()=>{try{return JSON.parse(localStorage.getItem(KEY)||'{}')||{}}catch{return {}}};
  const save=s=>{try{localStorage.setItem(KEY,JSON.stringify(s))}catch{}};
  const state=load();
  function apply(button,collapsed){
    const panel=document.getElementById(button.dataset.collapseTarget);
    if(!panel)return;
    panel.classList.toggle('collapsed',collapsed);
    button.setAttribute('aria-expanded',String(!collapsed));
    button.textContent=collapsed?'Expand':'Collapse';
  }
  function encounterSummary(){
    const out=document.getElementById('encounterSummary');if(!out)return;
    const pick=id=>{const s=document.getElementById(id);return s&&s.selectedOptions[0]?s.selectedOptions[0].textContent.trim():''};
    out.textContent=[pick('content_mode'),pick('boss_id')].filter(Boolean).join(' · ');
  }
  // Help text becomes an (i) tooltip. The original <small> elements are moved, not copied,
  // so app.js can keep updating them by id (encounter count, search cost, hints).
  function infoIcon(smalls){
    const icon=document.createElement('span');
    icon.className='info';icon.tabIndex=0;icon.setAttribute('role','button');icon.setAttribute('aria-label','More information');
    icon.textContent='i';
    const tip=document.createElement('span');tip.className='tip';tip.setAttribute('role','tooltip');
    smalls.forEach(s=>tip.appendChild(s));
    icon.appendChild(tip);
    icon.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();icon.classList.toggle('open');place(icon);});
    icon.addEventListener('mouseenter',()=>place(icon));
    icon.addEventListener('focus',()=>place(icon));
    icon.addEventListener('keydown',e=>{if(e.key==='Escape')icon.classList.remove('open')});
    return icon;
  }
  function place(icon){
    const r=icon.getBoundingClientRect();
    icon.classList.toggle('tip-left',r.left+300>document.documentElement.clientWidth-16);
  }
  document.addEventListener('click',e=>{document.querySelectorAll('.info.open').forEach(i=>{if(!i.contains(e.target))i.classList.remove('open')})});
  const settings=document.getElementById('settingsPanel');
  settings.querySelectorAll('label').forEach(label=>{
    if(label.classList.contains('chip'))return;
    const smalls=[...label.children].filter(c=>c.tagName==='SMALL');
    if(!smalls.length)return;
    const head=document.createElement('span');head.className='label-head';
    while(label.firstChild&&label.firstChild.nodeType===Node.TEXT_NODE)head.appendChild(label.firstChild);
    head.appendChild(infoIcon(smalls));
    label.insertBefore(head,label.firstChild);
  });
  const crit=document.getElementById('criticalPartsOption');
  if(crit){const s=[...crit.children].filter(c=>c.tagName==='SMALL');const l=crit.querySelector('label');if(s.length&&l)l.appendChild(infoIcon(s));}
  document.querySelectorAll('.requirements').forEach(req=>{const s=req.querySelector(':scope>small');const lg=req.querySelector('legend');if(s&&lg)lg.appendChild(infoIcon([s]));});

  // Must-include picker: up to five units from the loaded roster (app.js globals `roster`/`byId`).
  const MAX=5,mustKey='raidlab.mustInclude';
  let must=(()=>{try{return JSON.parse(localStorage.getItem(mustKey)||'[]')||[]}catch{return []}})();
  const input=document.getElementById('mustIncludeInput');
  const units=()=>{try{return roster.map(r=>byId[r.id]).filter(Boolean)}catch{return []}};
  const nameOf=id=>{try{return byId[id]?.name||id}catch{return id}};
  function renderMust(){
    const known=new Set(units().map(c=>c.id));
    if(known.size)must=must.filter(id=>known.has(id));
    const chips=document.getElementById('mustIncludeChips');
    chips.replaceChildren(...must.map(id=>{
      let c=null;try{c=byId[id]}catch{}
      const chip=document.createElement('span');chip.className='unit-chip';
      const dot=document.createElement('span');dot.className='element '+(c?.element||'');
      const label=document.createTextNode(nameOf(id));
      const x=document.createElement('button');x.type='button';x.textContent='×';x.setAttribute('aria-label','Remove '+nameOf(id));
      x.onclick=()=>{must=must.filter(m=>m!==id);saveMust();renderMust();};
      chip.append(dot,label,x);return chip;
    }));
    document.getElementById('mustIncludeCount').textContent=`${must.length}/${MAX}`;
    input.parentElement.hidden=must.length>=MAX;
    document.getElementById('mustIncludeOptions').replaceChildren(...units().filter(c=>!must.includes(c.id)).sort((a,b)=>a.name.localeCompare(b.name)).map(c=>{const o=document.createElement('option');o.value=c.name;return o;}));
  }
  function saveMust(){try{localStorage.setItem(mustKey,JSON.stringify(must))}catch{}}
  function pick(){
    const v=input.value.trim().toLowerCase();if(!v)return;
    const c=units().find(u=>u.name.toLowerCase()===v);
    if(c&&!must.includes(c.id)&&must.length<MAX){must.push(c.id);saveMust();input.value='';renderMust();}
  }
  input.addEventListener('input',pick);
  input.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();pick();}});
  input.addEventListener('focus',renderMust);
  new MutationObserver(renderMust).observe(document.getElementById('rows'),{childList:true});
  renderMust();

  document.querySelectorAll('.collapse-toggle').forEach(button=>{
    const id=button.dataset.collapseTarget;
    apply(button,!!state[id]);
    button.addEventListener('click',()=>{const next=button.getAttribute('aria-expanded')==='true';state[id]=next;save(state);apply(button,next);encounterSummary();});
  });
  ['content_mode','boss_id'].forEach(id=>document.getElementById(id)?.addEventListener('change',encounterSummary));
  new MutationObserver(encounterSummary).observe(document.getElementById('boss_id'),{childList:true});
  encounterSummary();
})();
