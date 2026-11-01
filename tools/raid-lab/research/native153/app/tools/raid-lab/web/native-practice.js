'use strict';
(() => {
  const get = id => document.getElementById(id);
  const names = new Map([[301701, 'Anis: Star'], [141207, 'Trina'], [110109, 'Drake'], [319111, 'Alice'], [422205, 'Scarlet']]);
  const storageKey = 'raid-lab-native-practice-job';
  const pendingStart = 'pending-start';
  const runLabel = get('native-run').textContent;
  let jobId = null, report = null, polling = false, starting = false, recovering = false, startUncertain = false, recoveredLatest = false;
  const number = value => BigInt(value).toLocaleString();
  function remember(id) { try { id ? sessionStorage.setItem(storageKey, id) : sessionStorage.removeItem(storageKey); } catch (_) {} }
  function busy(active) { get('native-run').disabled = active; get('native-cancel').hidden = !active; }
  async function api(path, body) {
    const response = await fetch(path, body === undefined ? {} : {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
    const data = await response.json();
    if (!response.ok) {
      const error = new Error(data.error || 'Request failed.');
      error.requestRejected = response.status >= 400 && response.status < 500;
      throw error;
    }
    return data;
  }
  function clearJob() { jobId = null; startUncertain = false; recoveredLatest = false; remember(null); busy(false); get('native-run').textContent = runLabel; }
  function uncertainStart(error) {
    startUncertain = true; remember(pendingStart); busy(false); get('native-run').textContent = 'Check start status';
    get('native-error').textContent = error ? error.message : '';
    get('native-status').textContent = 'The start request could not be confirmed. A battle may be running. Check its status before starting another.';
  }
  async function recoverStart() {
    if (recovering) return;
    recovering = true; busy(true); get('native-cancel').hidden = true;
    try {
      const response = await api('/api/native/practice/status');
      if (response.job === null) {
        clearJob(); get('native-error').textContent = '';
        get('native-status').textContent = 'No native job is recorded by the app. You can explicitly retry the start request.';
        return;
      }
      if (!response.job || !/^[a-f0-9]{24}$/.test(response.job.id)) throw new Error('The app did not return a valid recovery status.');
      jobId = response.job.id; startUncertain = false; recoveredLatest = true; remember(jobId);
      get('native-error').textContent = ''; await poll();
    } catch (error) { uncertainStart(error); }
    finally { recovering = false; }
  }
  function showResult(result) {
    report = result;
    get('native-score').textContent = number(result.score) + ' total damage';
    get('native-characters').replaceChildren();
    for (const character of result.characters) {
      const row = document.createElement('tr');
      for (const value of [names.get(character.tableId) || String(character.tableId), number(character.damage)]) {
        const cell = document.createElement('td'); cell.textContent = value; row.append(cell);
      }
      get('native-characters').append(row);
    }
    get('native-result').hidden = false;
  }
  async function poll() {
    if (polling || !jobId) return;
    polling = true;
    try {
      const state = await api('/api/jobs/' + jobId);
      const prefix = recoveredLatest ? 'Recovered latest native job. ' : '';
      get('native-status').textContent = prefix + (state.phase || 'Running original battle…');
      if (state.status === 'running') { setTimeout(poll, 1000); return; }
      if (!['done', 'cancelled', 'error'].includes(state.status)) throw new Error('Unexpected job status.');
      // A terminal response is different from losing transport. Release the
      // known job before rendering so malformed result data cannot strand it.
      clearJob(); get('native-error').textContent = '';
      if (state.status === 'done') { showResult(state.result); get('native-status').textContent = prefix + 'Battle complete.'; }
      else if (state.status === 'cancelled') get('native-status').textContent = prefix + 'Cancelled. Any started battle has closed.';
      else {
        get('native-error').textContent = state.error || 'The original battle could not finish.';
        get('native-status').textContent = prefix + 'Battle ended with an error. You can try again.';
      }
    } catch (error) {
      get('native-error').textContent = error.message;
      if (jobId) {
        get('native-status').textContent = 'Connection lost. Reconnect to this job to check its result.';
        busy(false); get('native-run').textContent = 'Reconnect to job';
      } else get('native-status').textContent = 'Battle finished, but its result could not be displayed.';
    } finally { polling = false; }
  }
  get('native-run').addEventListener('click', async () => {
    if (starting || polling || recovering) return;
    if (jobId) { busy(true); get('native-error').textContent = ''; await poll(); return; }
    if (startUncertain) { await recoverStart(); return; }
    try { if (sessionStorage.getItem(storageKey) === pendingStart) { await recoverStart(); return; } } catch (_) {}
    starting = true; report = null;
    busy(true); get('native-error').textContent = ''; get('native-result').hidden = true;
    get('native-status').textContent = 'Preparing original battle…';
    remember(pendingStart);
    try {
      const result = await api('/api/native/practice', {engine: 'original153', fixtureId: 'captured-fire90-run1', inputSourceSha256: '9660b4f952fbc86228d7537b3d8d59838d98cc8138aed5812d696dac7169f8c7', releaseId: 'native153-fire90-run1-v20-20261101'});
      if (!result || !/^[a-f0-9]{24}$/.test(result.id)) throw new Error('The app did not return a valid job identifier.');
      jobId = result.id; remember(jobId); await poll();
    } catch (error) {
      if (error.requestRejected) {
        clearJob(); get('native-error').textContent = error.message;
        get('native-status').textContent = 'The start request was rejected. You can try again.';
      } else uncertainStart(error);
    } finally { starting = false; }
  });
  get('native-cancel').addEventListener('click', async () => {
    if (!jobId) return;
    get('native-cancel').disabled = true;
    try { await api('/api/cancel/' + jobId, {}); get('native-status').textContent = 'Waiting for the current battle to close…'; }
    catch (error) { get('native-error').textContent = error.message; }
    finally { get('native-cancel').disabled = false; }
  });
  get('native-export').addEventListener('click', () => {
    if (!report) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], {type: 'application/json'}));
    const link = document.createElement('a'); link.href = url; link.download = 'original-engine-practice.json'; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  let saved = null;
  try { saved = sessionStorage.getItem(storageKey); } catch (_) {}
  if (saved && /^[a-f0-9]{24}$/.test(saved)) { jobId = saved; busy(true); poll(); }
  else if (saved === pendingStart) { uncertainStart(); recoverStart(); }
  else if (saved) remember(null);
})();
