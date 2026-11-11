'use strict';
// Encounter choices come from the installed client's original table catalogue.
window.RaidNativeEncounters = (() => {
  let entries = [], current = null, available = false, previewAvailable = false;
  const element = id => document.getElementById(id);
  const executionKey = 'raid-lab-native-execution-profile';
  const FAST_WAVES = [6302006, 6302009]; // Mirror Container, Kraken
  function fastAvailable(){return previewAvailable&&FAST_WAVES.includes(current?.waveId)&&current?.contentMode==='anomaly'&&element('nativeControlPolicy').value==='qte-parts-cover';}
  function selectExecution(){
    const allowed=fastAvailable(),saved=localStorage.getItem(executionKey);
    element('nativeExecutionProfile').replaceChildren(...(allowed?[option('accelerated60-preview','Accelerated preview · fastest available')]:[]),option('standard','Standard · real time'));
    element('nativeExecutionProfile').value=allowed&&saved==='accelerated60-preview'?'accelerated60-preview':'standard';
    element('nativeExecutionHint').textContent=allowed?'Original-engine preview with your selected builds and the original intro. Time varies by team; total elapsed time is shown after verification. Tested on one Mirror Container team and one Kraken team; other teams may differ.':'Standard original-engine execution.';
    searchCost();
  }
  const controlKey = 'raid-lab-native-control-policy';
  function selectControls() {
    const saved = localStorage.getItem(controlKey);
    element('nativeControlPolicy').value = ['auto','qte-parts-cover'].includes(saved) ? saved :
      (['anomaly','special'].includes(current?.contentMode) ? 'qte-parts-cover' : 'auto');
  }
  const option = (value, label, disabled = false) => {
    const node = document.createElement('option');
    node.value = value; node.textContent = label; node.disabled = disabled;
    return node;
  };
  function searchCost() {
    if (!current) return;
    const fast=element('nativeExecutionProfile').value==='accelerated60-preview';
    const depth = Number(element('budget').value);
    const count = Number(element('nativeTeams').value) * ({3:1,6:2,12:3}[depth]);
    const screen = {3:30,6:45,12:60}[depth];
    element('nativeSearchCost').textContent = fast?`About ${screen}s Python screening, then up to ${count} sequential battles. Time varies by team; verified elapsed time is shown with the results. Stop to keep completed results.`:`About ${screen}s Python screening, then up to ${count} battles, about ${Math.ceil(count * current.timeLimit / 60)} minutes of battle time plus loading. Stop after any battle to keep completed results.`;
  }
  function selected() {
    const previous = current;
    current = entries.find(row => row.id === element('boss_id').value) || null;
    const panel = element('bossSummary');
    panel.replaceChildren();
    if (!current) {
      panel.textContent = 'No encounters match this filter.';
      element('buildBtn').disabled = true; element('testTeam').disabled = true;
      element('nativeWeeklyLabel').hidden = true;
      return;
    }
    const title = document.createElement('h3'); title.textContent = current.name;
    const details = document.createElement('p');
    const rule = current.unitLevel || {};
    const level = rule.mode === 'fixed' ? `Level ${rule.value}` : rule.mode === 'cap' ? `Your levels, capped at ${rule.value}` : 'Your unit levels';
    details.textContent = `${current.timeLimit}s limit · ${level}`;
    const description = document.createElement('small');
    description.textContent = current.selectable === false ? (current.reason || 'This stage requires its original preset squad.') : 'Original enemies, phases, parts and battle rules. Your selected squad uses its saved gear and skills.';
    panel.append(title, details, description);
    element('nativeWeeklyLabel').hidden = current.contentMode !== 'museum';
    if (current.id !== previous?.id) {
      element('nativeWeeklyBuff').replaceChildren(option('0','No weekly buff'),
        ...(current.weeklyBuffOptions || []).map(row => option(row.id, row.name)));
    }
    selectControls();
    selectExecution();
    element('duration').value = current.timeLimit;
    const multi = ['solo','museum'].includes(current.contentMode);
    element('nativeTeams').disabled = !multi;
    if (!multi) element('nativeTeams').value = '1';
    searchCost();
    element('buildBtn').disabled = current.selectable === false;
    element('testTeam').disabled = current.selectable === false;
    localStorage.setItem('raid-lab-native-encounter', current.id);
  }
  function filter(preferred) {
    if (!available) return;
    const mode = element('content_mode').value;
    const choices = entries.filter(row => row.contentMode === mode);
    const old = preferred || current?.id || element('boss_id').value;
    element('boss_id').replaceChildren(...choices.map(row => option(row.id, row.name + (row.selectable === false ? ' · unavailable' : ''), row.selectable === false)));
    const next = choices.find(row => row.id === old && row.selectable !== false) || choices.find(row => row.selectable !== false);
    if (next) element('boss_id').value = next.id;
    element('encounterCount').textContent = `${choices.length} encounter${choices.length === 1 ? '' : 's'}`;
    selected();
  }
  async function init(api) {
    const data = await api('native/encounters');
    const health = await api('health');previewAvailable=health.acceleratedPreview===true&&health.acceleratedPreviewVersion===2;
    if (data.engine !== 'original153' || !Array.isArray(data.encounters) || !data.encounters.length) throw Error('Original encounter catalogue is unavailable.');
    entries = data.encounters;
    const names = {anomaly:'Anomaly Interception',special:'Special Interception',solo:'Solo Raid',museum:'Solo Raid Museum',campaign:'Campaign',practice:'Practice'};
    const modes = data.modes || Object.keys(names).filter(id => entries.some(row => row.contentMode === id)).map(id => ({id,name:names[id]}));
    element('content_mode').replaceChildren(...modes.map(row => option(row.id, row.name)));
    const saved = entries.find(row => row.id === localStorage.getItem('raid-lab-native-encounter') && row.selectable !== false);
    const initial = saved || entries.find(row => row.bossId === 'anomaly-kraken' && row.selectable !== false) || entries.find(row => row.selectable !== false);
    if (initial) element('content_mode').value = initial.contentMode;
    element('content_mode').disabled = false;
    element('boss_id').disabled = false;
    available = true;
    element('nativeControlPolicy').addEventListener('change', () => {localStorage.setItem(controlKey, element('nativeControlPolicy').value);selectExecution();});
    element('nativeExecutionProfile').addEventListener('change',()=>{localStorage.setItem(executionKey,element('nativeExecutionProfile').value);searchCost();});
    element('nativeTeams').addEventListener('change', searchCost);
    element('budget').addEventListener('change', searchCost);
    filter(initial?.id);
  }
  function settings() {
    if (!available || !current || current.selectable === false) throw Error('Choose a supported original encounter.');
    const value = {encounter_id:current.id,control_policy:element('nativeControlPolicy').value};
    if(previewAvailable)value.execution_profile=element('nativeExecutionProfile').value;
    if (current.contentMode === 'museum') value.weekly_buff_id = Number(element('nativeWeeklyBuff').value);
    return value;
  }
  return {init,filter,selected,settings};
})();
