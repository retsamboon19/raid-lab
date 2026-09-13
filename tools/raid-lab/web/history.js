'use strict';

// History owns its state and reads snapshots only; encounter controls and live results are separate.
const RaidHistory = (() => {
 const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const fmt = value => Number.isFinite(value) ? new Intl.NumberFormat('en', {notation:'compact', maximumFractionDigits:2}).format(value) : '—';
 const date = value => {const d = new Date(value); return Number.isNaN(d.valueOf()) ? 'Date unavailable' : d.toLocaleString(undefined, {dateStyle:'medium', timeStyle:'short'});};
 const squadCount = run => `${run.teams.length}${run.requested_teams > run.teams.length ? '/'+run.requested_teams : ''} squad${run.teams.length === 1 && !(run.requested_teams > 1) ? '' : 's'}`;
 const context = run => [squadCount(run), run.mode === 'museum' ? (run.museum_mode === 'no-limit' ? 'No Limit' : 'Challenge') : '', run.duration ? run.duration+'s each' : '', run.kind === 'manual' ? 'Manual team' : run.kind === 'legacy' ? 'Imported saved report' : 'Team search'].filter(Boolean).join(' · ');
 function damageAccounting(team, nameForId=id=>id) {
  const accounting=team.damage_accounting;
  if(!accounting)return '';
  const ids=[...new Set([...(team.members||[]),...Object.keys(accounting.by_unit||{})])];
  const amount=value=>Number.isFinite(value)?fmt(value):'<span class="muted">Not recorded</span>';
  return `<details class="support-plan damage-accounting"><summary>Damage accounting</summary><p><strong>Direct boss damage: ${amount(accounting.boss_direct)}</strong> · Part-break bonus: ${amount(accounting.part_break_bonus)} · Total boss HP loss: ${amount(accounting.boss_hp_loss)}</p><div class="table-scroll"><table><thead><tr><th scope="col">Nikke</th><th scope="col">Boss</th><th scope="col">Summons</th><th scope="col">All targets</th></tr></thead><tbody>${ids.map(id=>{const row=accounting.by_unit?.[id]||{};return `<tr><th scope="row">${esc(nameForId(id))}</th><td>${amount(row.boss_direct)}</td><td>${amount(row.summon_direct)}</td><td>${amount(row.all_targets_direct)}</td></tr>`;}).join('')}</tbody><tfoot><tr><th scope="row">Direct damage total</th><td>${amount(accounting.boss_direct)}</td><td>${amount(accounting.summon_direct)}</td><td>${amount(accounting.all_targets_direct)}</td></tr></tfoot></table></div><p class="muted">The all-target total includes raw damage to summons, including overkill, for comparison with Battle Records. Direct boss damage excludes summon hits. Part-break bonuses remove boss HP but are shown separately and are not credited to individual Nikke.</p></details>`;
 }
 function runCard(run, first) {
  return `<details class="history-run panel" ${first ? 'open' : ''}><summary><span class="history-run-title"><time datetime="${esc(run.created_at)}">${esc(date(run.created_at))}</time><span class="muted">${esc(context(run))}</span>${run.completion_reason === 'cancelled' ? '<span class="history-status">Cancelled · best completed results</span>' : ''}</span><span class="history-run-total"><strong>${fmt(run.total)}</strong><small>${run.total == null ? 'Composition only' : run.damage_basis === 'boss_direct' ? 'Direct boss damage' : 'Combined damage'}</small></span><span class="history-chevron" aria-hidden="true">⌄</span></summary><div class="history-run-body"><div class="history-lineups">${run.teams.map(t => `<div class="history-lineup"><span class="history-squad-label">Squad ${esc(t.index)}</span><div class="history-members">${(t.members || []).map(m => `<span><i class="element ${esc(m.element)}" aria-hidden="true"></i>${esc(m.name || m.id)}</span>`).join('')}</div><strong>${fmt(t.damage)}</strong></div>`).join('')}</div><div class="history-run-footer"><small>${run.critical_parts ? `${esc(run.critical_parts.passed_teams)}/${esc(run.critical_parts.total_teams)} squads met modeled part deadlines` : 'Saved squad order and investment'}${run.critical_parts?.fallback ? ' · best tested fallback' : ''}</small><button data-history-open="${esc(run.id)}">View full report <span aria-hidden="true">↗</span></button></div></div></details>`;
 }
 function create({root, api, feedback, getCatalog, download, checks, getModelRevision=()=>null}) {
  const state = {modes:[], mode:'', boss:'', runs:[], total:0, hasMore:false, loaded:false, dirty:true, listToken:0, detailToken:0, detail:null};
  root.innerHTML = `<div id="historyBrowse"><section class="panel history-controls"><div class="history-heading"><div><p class="eyebrow">SAVED RUNS</p><h2>Recommendation history</h2><p class="muted">Choose a mode, then a boss. Each run keeps all its squads together.</p></div><span class="history-local">Saved on this PC</span></div><div class="history-filters"><label><span><b>1</b> Mode</span><select id="historyMode"><option value="">Choose a mode</option></select></label><label><span><b>2</b> Boss</span><select id="historyBoss" disabled><option value="">Choose a mode first</option></select></label></div></section><div id="historyStatus" class="history-status-line" role="status" aria-live="polite"></div><div id="historyRuns"></div><button id="historyMore" class="quiet" hidden>Load older runs</button></div><div id="historyDetail" hidden></div>`;
  const el = id => root.querySelector('#'+id);
  function populateFilters() {
   el('historyMode').innerHTML = '<option value="">Choose a mode</option>'+state.modes.map(m => `<option value="${esc(m.id)}">${esc(m.name)}</option>`).join('');
   el('historyMode').value = state.mode;
   const mode = state.modes.find(m => m.id === state.mode);
   el('historyBoss').disabled = !mode;
   el('historyBoss').innerHTML = `<option value="">${mode ? 'Choose a boss' : 'Choose a mode first'}</option>`+(mode?.bosses || []).map(b => `<option value="${esc(b.id)}">${esc(b.name)} · ${b.count} run${b.count === 1 ? '' : 's'}</option>`).join('');
   el('historyBoss').value = state.boss;
  }
  function status(message, retry) {
   el('historyStatus').innerHTML = `<p>${esc(message)}</p>${retry ? '<button id="historyRetry" class="quiet">Try again</button>' : ''}`;
   if(retry) el('historyRetry').onclick = () => load(false);
  }
  async function load(append = false) {
   const token = ++state.listToken, mode = state.mode, boss = state.boss;
   const filtered = Boolean(mode && boss), offset = append ? state.runs.length : 0;
   if(!append) {state.runs = []; el('historyRuns').innerHTML = '';}
   el('historyMore').hidden = true;
   status('Loading saved runs…');
   try {
    const query = filtered ? `?mode=${encodeURIComponent(mode)}&boss=${encodeURIComponent(boss)}&offset=${offset}&limit=10` : '';
    const data = await api('history'+query);
    if(token !== state.listToken) return;
    // A newly saved run shifts offset pages; refresh instead of duplicating or skipping entries.
    if(append && data.total !== state.total) return load(false);
    state.modes = data.modes; state.loaded = true; state.dirty = false;
    state.runs = append ? [...state.runs, ...data.runs] : data.runs;
    state.total = data.total; state.hasMore = data.has_more;
    populateFilters();
    if(!state.modes.length) status('No saved runs yet. Recommendations are saved automatically when a search or team simulation returns results, including completed results kept after cancellation.');
    else if(!mode) status('Select a mode to see its bosses.');
    else if(!boss) status('Select a boss to see previous recommendations.');
    else if(!state.runs.length) status('No saved runs for this boss yet.');
    else status(`${state.total} saved run${state.total === 1 ? '' : 's'} · newest first. Expand a run to compare its squads.`);
    if(append) el('historyRuns').insertAdjacentHTML('beforeend', data.runs.map(r => runCard(r, false)).join(''));
    else el('historyRuns').innerHTML = state.runs.map((r,i) => runCard(r,i === 0)).join('');
    el('historyMore').hidden = !state.hasMore;
    if(append) root.querySelectorAll('.history-run > summary')[offset]?.focus();
   } catch(error) {if(token === state.listToken) status('Could not load history. '+error.message, true);}
  }
  el('historyMode').onchange = () => {state.mode = el('historyMode').value; state.boss = ''; populateFilters(); load();};
  el('historyBoss').onchange = () => {state.boss = el('historyBoss').value; load();};
  el('historyMore').onclick = () => load(true);
  async function back() {
   ++state.detailToken; state.detail = null; el('historyDetail').hidden = true; el('historyBrowse').hidden = false;
   if(state.dirty) await load();
   const button = Array.from(root.querySelectorAll('[data-history-open]')).find(b => b.dataset.historyOpen === state.openId);
   (button || el('historyMode')).focus();
  }
  async function open(id) {
   const token = ++state.detailToken; state.openId = id;
   el('historyBrowse').hidden = true; el('historyDetail').hidden = false;
   el('historyDetail').innerHTML = '<button data-history-back class="quiet">← Back to history</button><p role="status">Loading saved report…</p>';
   try {
    const data = await api('history/'+encodeURIComponent(id));
    if(token !== state.detailToken) return;
    state.detail = data; renderDetail(data);
    el('historyDetail').scrollIntoView({block:'start',behavior:'instant'});
    el('historyDetailTitle').focus({preventScroll:true});
   } catch(error) {
    if(token !== state.detailToken) return;
    el('historyDetail').innerHTML = `<button data-history-back class="quiet">← Back to history</button><p role="alert">${esc(error.message)}</p><button data-history-open="${esc(id)}">Try again</button>`;
   }
  }
  root.addEventListener('click', event => {
   const button = event.target.closest('button'); if(!button) return;
   if(button.hasAttribute('data-history-back')) back();
   else if(button.dataset.historyOpen) open(button.dataset.historyOpen);
   else if(button.hasAttribute('data-history-export') && state.detail) download('raid-lab-history-'+state.detail.id+'.json', state.detail.report);
   else if(button.hasAttribute('data-history-feedback') && state.detail && feedback) feedback(state.detail.report, Number(root.querySelector('[data-history-squad][aria-selected="true"]')?.dataset.historySquad||0));
   else if(button.dataset.historySquad !== undefined) selectSquad(Number(button.dataset.historySquad));
  });
  root.addEventListener('keydown', event => {
   const button = event.target.closest('[data-history-squad]'); if(!button) return;
   const count = state.detail.report.teams.length, index = Number(button.dataset.historySquad);
   const next = {ArrowRight:(index+1)%count, ArrowLeft:(index+count-1)%count, Home:0, End:count-1}[event.key];
   if(next !== undefined) {event.preventDefault(); selectSquad(next); el('historySquadTab'+next).focus();}
  });
  function selectSquad(index) {
   root.querySelectorAll('[data-history-squad]').forEach(b => {const active = Number(b.dataset.historySquad) === index; b.setAttribute('aria-selected', String(active)); b.tabIndex = active ? 0 : -1;});
   root.querySelectorAll('[data-history-panel]').forEach(p => {p.hidden = Number(p.dataset.historyPanel) !== index;});
   root.querySelector('.history-squad-deck')?.scrollIntoView({block:'start',behavior:'instant'});
  }
  function renderDetail(data) {
   const report = data.report, summary = data.summary, settings = report.settings || {}, teams = report.teams || [];
   const snapshots = Object.fromEntries((summary.teams || []).flatMap(t => t.members).map(m => [m.id,m]));
   const catalog = getCatalog();
   const unit = id => ({...(catalog[id] || {}), ...(snapshots[id] || {}), name:snapshots[id]?.name || catalog[id]?.name || id});
   const names = Object.fromEntries(teams.flatMap(t => t.members).map(id => [id,unit(id).name]));
   const name = id => esc(names[id] || unit(id).name);
   const jsonDetails = (title, value) => value == null ? '' : `<details><summary>${esc(title)}</summary><pre>${esc(JSON.stringify(value,null,2))}</pre></details>`;
   const modeName = state.modes.find(m => m.id === summary.mode)?.name || summary.mode;
   el('historyDetail').innerHTML = `<div class="history-detail-toolbar"><button data-history-back class="quiet">← Back to history</button><button data-history-feedback>Give feedback</button><button data-history-export>Export report</button></div><div class="panel report-header"><div><p class="eyebrow">SAVED RECOMMENDATION · ${esc(date(data.created_at))}</p><h2 id="historyDetailTitle" tabindex="-1">${esc(summary.boss_name)}</h2><div class="total">${fmt(summary.total)}</div>${summary.total!=null&&teams.every(t=>t.damage_accounting)?'<small class="muted">Direct boss damage</small>':''}<p>${esc(modeName)} · ${esc(context(summary))}</p></div><div><span class="history-local">Read-only snapshot</span><p>${summary.total == null ? 'Composition assessment' : teams.every(t=>t.damage_accounting) ? 'Direct boss damage' : 'Combined simulated damage'}<br>${esc(report.simulations ?? '—')} simulations · ${esc(report.elapsed ?? '—')}s search</p></div></div>${summary.completion_reason === 'cancelled' || teams.length < summary.requested_teams ? `<div class="stale">Best completed results when the search stopped · ${esc(squadCount(summary))}. Untested candidates may improve this result.</div>` : ''}${getModelRevision() && summary.model_revision !== getModelRevision() ? '<p class="history-model-note">Saved with an earlier model. Scores and mechanic coverage may differ from a new search.</p>' : ''}<p class="muted">Saved results use the builds and settings from this run. Modeled checks do not certify an in-game clear.</p>${report.selection?.critical_parts ? `<section class="support-plan"><h4>${report.selection.critical_parts.fallback ? 'Critical-part fallback' : 'Critical-part requirement met'}</h4><p>${esc(report.selection.critical_parts.message)}</p><small>${esc(report.selection.critical_parts.scope)}</small></section>` : ''}<div class="history-squad-deck">${teams.length > 1 ? `<nav class="squad-tabs" role="tablist" aria-label="Saved squads">${teams.map((t,i) => `<button role="tab" id="historySquadTab${i}" data-history-squad="${i}" aria-controls="historySquadPanel${i}" aria-selected="${i === 0}" tabindex="${i === 0 ? 0 : -1}"><span>Squad ${i+1}</span><small>${fmt(t.damage)}</small></button>`).join('')}</nav>` : ''}${teams.map((t,i) => {
    const maximum = Math.max(1,...Object.values(t.breakdown || {}));
    let checkItems = [];
    try { checkItems = checks(t, settings, names); } catch { /* Older snapshots can lack fields expected by newer check code. */ }
    const fight = t.encounter_timeline;
    return `<article class="panel squad" id="historySquadPanel${i}" data-history-panel="${i}" ${teams.length > 1 ? `role="tabpanel" aria-labelledby="historySquadTab${i}" tabindex="0"` : ''} ${i ? 'hidden' : ''}><div class="squad-head"><div><p class="eyebrow">SQUAD ${String(i+1).padStart(2,'0')}</p><h3>${esc(t.bursts ?? '—')} Full Bursts</h3></div><div class="score">${fmt(t.damage)}<p class="muted">${t.damage_accounting?'Direct boss damage<br>':''}${fmt(t.dps)} DPS</p></div></div><div class="squad-members">${t.members.map((id,j) => {const c = unit(id); return `<div class="member"><span class="slot">0${j+1} / B${esc(c.burst ?? '?')}</span><strong>${name(id)}</strong><small>${esc(c.element || 'Unknown element')}${c.weapon ? ' · '+esc(c.weapon) : ''}</small><div class="bar-track"><div class="bar-fill" style="width:${Math.min(100,Math.max(0,100*(t.breakdown?.[id] || 0)/maximum))}%"></div></div><small>${fmt(t.breakdown?.[id])} damage</small></div>`;}).join('')}</div>${damageAccounting(t,id=>unit(id).name||id)}${checkItems.length ? `<section class="squad-checks"><h4>Saved squad evidence</h4><div class="history-checks">${checkItems.map(c => `<details class="history-check check-${esc(c.state)}"><summary><span class="check-icon" aria-hidden="true">${({pass:'✓',fail:'×',warn:'!',unknown:'?',info:'i'})[c.state] || '?'}</span><span><strong>${esc(c.label)}</strong><small>${esc(c.value)}</small></span></summary><p>${esc(c.detail)}</p></details>`).join('')}</div></section>` : '<p class="muted">Squad checks were not recorded in this older report.</p>'}${fight?.off_burst_controller ? `<section class="support-plan"><h4>Off-burst control: ${name(fight.off_burst_controller)}</h4><p>Aim at the critical part outside Full Burst. The saved control plan and timing are below.</p>${(fight.control_plan || []).map(p => `<p>${esc(p.start)}–${esc(p.end)}s · ${name(p.unit)} → ${esc(fight.part_labels?.[p.part] || p.part)} · ${fmt(p.damage)} targeted damage</p>`).join('')}</section>` : ''}${t.recommendation?.rationale ? `<section class="support-plan"><h4>Why this team</h4><p>${esc(t.recommendation.rationale.overview)}</p><p>${esc(t.recommendation.rationale.boss_fit)}</p>${(t.recommendation.rationale.interactions || []).map(c => `<p><strong>${esc(c.title)}</strong><br>${esc(c.why)}<br><small>${esc(c.condition)}</small></p>`).join('')}</section>` : ''}${t.support_plan ? `<section class="support-plan"><h4>Survival & cover plan</h4><p>${esc(t.support_plan.summary)}</p><p>${esc(t.support_plan.cover_policy)}</p><small>${esc(t.support_plan.warning)}</small></section>` : ''}${fight?.model ? `<section class="support-plan"><h4>Recorded boss outcomes</h4><p>${esc(fight.survival)} · simulated to ${esc(fight.simulated_until)}s. ${esc(fight.stop_reason)}</p>${(fight.critical_deadlines || fight.critical_parts || []).map(p => `<p>${esc(p.part || p.id)} · ${esc(p.status)}${p.deadline != null ? ' · deadline '+esc(p.deadline)+'s' : ''}${p.destroyed_at != null ? ' · destroyed '+esc(p.destroyed_at)+'s' : ''}</p>`).join('')}${jsonDetails('Boss actions, incoming damage and cover',fight)}</section>` : ''}${(t.reasons || []).map(r => `<p>${esc(r)}</p>`).join('')}${(t.warnings || []).map(w => `<p class="warning">${esc(w)}</p>`).join('')}<details><summary>Burst sequence</summary><div class="burst-list">${(t.burst_log || []).map(e => `<span class="burst-event">${esc(e.time)}s · ${esc(e.event === 'full_burst 시작' ? 'Full Burst starts' : e.event === 'full_burst 종료' ? 'Full Burst ends' : e.event)}${e.unit ? ' · '+name(e.unit) : ''}</span>`).join('') || '<p>Not recorded in this report.</p>'}</div></details>${jsonDetails('Exact saved builds',t.builds)}${jsonDetails('All saved squad details',t)}</article>`;
   }).join('')}</div><section class="panel limitations"><h2>Saved assumptions and settings</h2><ul>${[...(report.limitations || []),...(report.warnings || []),...(report.assumptions || [])].map(x => `<li>${esc(x)}</li>`).join('')}</ul>${jsonDetails('Encounter and search settings',settings)}${jsonDetails('Selection evidence',report.selection)}</section>`;
  }
  return {show() {if(!state.loaded || state.dirty) load();}, invalidate() {state.dirty = true; if(!root.hidden && !state.detail) load();}, state};
 }
 return {create, runCard, context, squadCount, damageAccounting};
})();
if(typeof module !== 'undefined') module.exports = RaidHistory;
