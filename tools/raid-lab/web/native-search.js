'use strict';
window.RaidNativeSearch = (() => {
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const exact = value => {try {return BigInt(value).toLocaleString('en');} catch {return 'Unavailable';}};
  function render(report, catalog, editable = true) {
    let html = `<section class="panel report-header"><div><p class="eyebrow">ORIGINAL ENGINE · AUTOMATIC TEAM SEARCH</p><div class="total">${exact(report.total)}</div><p>${report.teams.length} non-overlapping squad${report.teams.length === 1 ? '' : 's'} · ${esc(report.settings.encounter.name)}</p></div><p>${report.simulations} completed battles · ${esc(report.elapsed)}s elapsed</p></section>`;
    if(report.screening)html += `<p>Python completed ${esc(report.screening.simulations)} screening simulations in ${esc(report.screening.elapsed)}s; ${report.simulations} engine battles verified the finalists. Python estimates are used only for shortlisting.</p>`;
    const accelerated=report.settings?.execution_profile==='accelerated60-preview'||report.candidates?.[0]?.executionProfile?.id==='accelerated60-preview';
    html += `<p>${accelerated?'Accelerated preview':'Standard'} · ${report.requestTiming?.acceptedToVerifiedSeconds!=null?esc(report.requestTiming.acceptedToVerifiedSeconds)+'s request to verified results':'Search elapsed time includes candidate execution'}</p>`;
    if(accelerated)html+=`<p class="warning">Original-engine preview. Tested on one reference team; results for other teams are not yet established.</p>`;
    if (report.completion.reason !== 'completed') html += `<p class="panel warning">Search stopped (${esc(report.completion.reason)}). Keeping ${report.teams.length} of ${report.completion.requested_teams} requested squads from completed battles.</p>`;
    html += `<p>${esc(report.selection.objective)}. ${esc(report.selection.method)}</p>`;
    report.teams.forEach((team, index) => {
      const battle = team.native, outcome = battle.nativeOutcome || {};
      html += `<article class="panel squad"><div class="squad-head"><h3>Squad ${index + 1}</h3><strong>${exact(team.damage)} ${battle.gameTotalDamage!=null?'game total damage':'native aggregate'}</strong>${editable ? `<button class="quiet" data-manual="${index}">Adjust &amp; simulate</button>` : ''}</div><div class="squad-members">`;
      team.members.forEach((id, slot) => {
        const row = battle.characters.find(r => Number(r.slot) === slot + 1);
        html += `<div class="member"><span class="slot">Slot ${slot + 1} · B${esc(catalog[id]?.burst)}</span><strong>${esc(catalog[id]?.name || id)}</strong><small>${exact(row?.damage)} native aggregate</small></div>`;
      });
      html += `</div><p>${esc(battle.durationMs / 1000)}s · ${outcome.targetRemainHp != null ? (String(outcome.targetRemainHp) === '0' ? 'Clear' : 'Not cleared') : 'Clear status unavailable'} · ${esc(outcome.survivingPlayerCount ?? 'Unknown')} members remaining</p><p>Target HP: ${exact(outcome.targetRemainHp)} / ${exact(outcome.targetMaxHp)}</p>`;
      if (battle.tactical?.unsupported?.length) html += `<p class="warning">${battle.tactical.unsupported.map(esc).join('; ')}</p>`;
      html += `<details><summary>Saved builds, burst slot order and original battle evidence</summary><pre>${esc(JSON.stringify(battle, null, 2))}</pre></details></article>`;
    });
    html += `<details class="panel"><summary>All ${report.simulations} completed candidate battles</summary>${report.candidates.map(battle => `<p>${battle.requestedInputs.members.map(id => esc(catalog[id]?.name || id)).join(' → ')} · ${exact(battle.gameTotalDamage??battle.score)} ${battle.gameTotalDamage!=null?'game total damage':'native aggregate'} · ${esc(battle.durationMs / 1000)}s</p>`).join('')}</details>`;
    if (report.failures.length) html += `<section class="panel warning">${report.failures.map(f => `<p>${esc(f.error)}</p>`).join('')}</section>`;
    html += `<section class="panel limitations"><ul>${report.limits.map(value => `<li>${esc(value)}</li>`).join('')}</ul></section>`;
    return html;
  }
  return {render};
})();
