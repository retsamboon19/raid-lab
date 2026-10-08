# Native smarter autoplay implementation — October 8, 2026

## All-boss scope correction and current work — October 9

The user explicitly corrected stopping at Kraken: the task covers ALL selectable
Raid Lab boss fights, with smarter targeting, boss mechanics, cover and resumption.
Kraken is a checkpoint, not completion. No visual gameplay is requested.

`BOSS-AUTOPLAY-COVERAGE.json` inventories all23 selector entries:21 fixed boss
variants plus training/campaign. All32 selected current wave rows (including
Museum challenge/no-limit) are available. `BOSS-TACTICAL-SOURCE-RULES.json` binds
current monster/skill/part/QTE rows; retained BT node mappings are explicitly
unverified against installed BT bytes until checked. Source mapping is not a
native tactics pass. Production search remains Python.

New `boss-tactical` mode uses `mechanics_qte_policy.js` (live Break-only targets,
orders/deadlines, repeated presets, original input and native outcomes) and
`mechanics_cover_policy.js` (per-caster live threats, source-scoped rules, repeats
and ownership). Only Kraken's known attack has a native-tested cover rule; do not
copy it to penetrating attacks such as Mirror Shot16. Extended passive observers
retain live monster table IDs, per-caster attack cursors and preset identities.

Trial122 completed the original battle and exited normally, but its immutable
tactical receipt FAILED. It rejected native collider index0; confused cumulative
ring-buffer eviction with missed attacks; and stamped post-projectile casting
with sampled action time, releasing5271 instead of5055. Fixes use zero-based
collider IDs, per-caster attack ordinals, and original condition-transition time.
Original QuickTimePresetStart0x064A5E20 uses event.Index as a preset/group key,
separate from context._currentIndex; the reusable policy now preserves that.
The repeat123 command is the same exact request/mode after these concrete fixes.
Do not reuse122 as passing evidence or repeat its unchanged failed controller.

`mechanics-encounters-current.json` and `mechanics_encounters.py` register ten
current Special/Anomaly profiles and verify exact current MPK/client/decoder
sources. Request schema2 binds profile ID, native transporter values and original
level caps; schema1 preserves archived Kraken inputs. Unmapped original fields
remain explicit limitations. Only staged geometry may run, despite ten registered
profiles. Mirror current wave6302006/target4510010123/map
sbg_cityforestcrystalxba001_001 is prepared: source manifest SHA
d1c334def34ae73ed4344c4f79e1f00431f35df49e1fc7eefc562b0c1095f306,
staging receipt fe659cba0e38f478d13201c40560c3a7c9ae6bb055d1b9765aec436bf39b5040.
1481 new source-verified chunks were added after122 exited, preserving prior
resources and a backed-up receipt; no installed client/account mutation.
Trial123 now PASSES the generic QTE and cover validators. Original 180-second
battle completed; seven Break targets hit, no observed Counter damage, all five
survive, cover releases at5055 and native firing resumes. Its complete numerical
result is identical to120 (989785848damage, boss remaining4404214152). Ticks took
25.436s; private host36.628s. Plan
ec5680dd82a6bd20490a437618e4cb0d041ed50d1b71137418ee855e548fff30;
frozen bundle7c7f13bd947b9d06527ca78275a2cf9adaafb1c23abbf6cf26a2f0c2f6dd12c3;
log e0229e00690da4908e545775182e39500efa722abff0e11b277ba2545100d5ca.
This validates the reusable controller on the known Kraken case only. Mirror
has not run. Its schema2 request SHA is
55791f1dfc558378c1ec8bb2209baef6e738f004e289eeab8fdfa8516901a7c7.
Current user follow-up requests publishing all Raid Lab progress to GitHub main.
Freeze this checkpoint for publication, then resume Mirror's native run as124.
No private native process remains.

User authorized implementation after the feasibility assessment, emphasizing efficient investigation. Objective remains results-only original combat, with smarter player inputs. No visual reconstruction, alternative damage engine, production server restart, installed client/catalog/hook change, account mutation, or warm-reuse optimization.

## Current result

Latest combined `kraken-tactical-v2` passes in native trials 120/121. It protects all five units through the node230 missile and follow-up blast, resumes native firing, hits all seven Break targets in group212 with no observed Counter damage, receives the original successful preset-end event at tick5438 and restores auto. Full numerical results and all192 retained tactical observations/events/decisions match at default and180 wall FPS. Native input/cover/QTE validators pass automatically.

All five survive, versus three in original-auto baseline104/116. Original damage is989785848 versus1017313717 (about2.7% lower): this first conservative cover policy demonstrates survival/mechanical handling, not optimal damage. Cover begins at4695 and ends5055, waiting for projectiles AND native Idle after the follow-up cast. A tighter safe cover window is future optimization, not a claimed result.

This is one exact fixture, attack sequence and QTE group, not all bosses, normal-game parity, complete equipped builds, or production integration. Production Raid Lab search still uses Python. Earlier QTE-only114/115 passed independently; the implementation/failures below preserve the progression.

## Implementation and source boundaries

- `mechanics_tactical_actions.js`: original auto-mode event, TagCharacterEvent selection, live-camera projection through SpotDriver.MoveAimPosition, original point down/up, and squad forced cover. Readbacks include focus, input, stance, spent ammo, hit count, squad stance/ammo and virtual pointer lease. No direct combat-state writes.
- `mechanics_virtual_pointer.js`: retains original Input.get_mousePosition execution; substitutes x/y only for the exact KeyInputContext callsite return RVA `0x0649EEF0`, on its main thread and while the policy owns virtual input. Original z and every other caller remain untouched. Exact call bytes `e86009e201` at `0x0649EEEB`; getter `0x082BF850` uses an output Vector3 pointer. No managed calls in this native callback. Lease is cleared on return to auto; hook remains until private process exit.
- `mechanics_tactical_observer.js`: passive QTE targets/types/order/time/HP/position, original preset success, current monster parts, squad/cover HP, current weapon/ammo, original attack/breakable/QTE events. Exact metadata/RVA guards; bounded collection sizes; explicit unsupported subgroups. Existing SendEventDefault hook forwards events; no new event hook.
- `mechanics_tactical_controller.js`: unchanged `original`, passive `observe`, bounded input `probe`, or reactive `kraken-qte`. Observes every three native ticks, issues input before original UpdateSpot. Mode and policy version are emitted and bound to archived bundle/request receipt.
- `mechanics_kraken_qte_policy.js`: supports observed group212; three ticks reaction plus three ticks settling on each new target, live target tracking, ready SMG then AR then MG selection, Break-only shots, release on target loss, original-auto restoration on native preset result. Trial119 showed earlier-slot MG was too slow; v2 explicitly prioritizes the SMG class already proven to finish this short sequence. This is not a universal weapon DPS rank. It never targets Counter/Choice, reads future RNG, writes HP, or fabricates success.
- `mechanics_kraken_cover_probe.js`: event-triggered original whole-squad cover for node230. Holds through active boss projectiles and subsequent FireCasting/Fire until native Idle, then restores and verifies actual firing. `kraken-tactical` combines this with QTE policy. Simultaneous QTE/cover ownership outside the validated sequence fails explicitly; repeated attack episodes/other nodes are not certified.
- `mechanics_threat_observer.js`: passive original attack, boss projectile create/spawn/despawn and character/cover damage events. Logging is focused from nodes229/230 to preserve the relevant sequence within a bounded200 records. Exact skill-to-projectile binding remained unknown because intervening dispatches separate Create and Spawn; policy conservatively waits for all observed boss projectiles rather than guessing that association.
- `run_trial.py` / `stage_probe.py`: explicit `--control-mode`, frozen bundle binding and automatic native input/QTE evidence validators for their respective modes.

Manual release was resolved through TeamContext.OnGetInputEvent `0x064EFA40`: original InputPointUp event ID 74000 maps to CheckChangeStanceEvent stance 0, separately from the aim-auto-only BTContext branch. Original input down maps to stance 2.

QTE rules: preset IsSuccess `0x06375ED0` requires all Break colliders disabled; OnQuickTimeColliderHit `0x064A56E0` fails on destroyed Counter colliders. Group 212 targets have order 0; current order 999 is not an instruction to shoot Counter. Current table row QuickTimeEvent 10121 is Iron 500001, weak to Wind 300001. Original damage code adds the weakness bonus; element mismatch does not establish an immunity gate. Native Liter SMG shots in 114/115 actually resolved the Break targets. Preserve original collision, spread and damage rules.

## Discriminating trials and regression evidence

All trials used the exact original snapshot request `mechanics_request_snapshot.json`, SHA `b66e3922a384cb31cc7a05032400485bf6c9dce7f9d9b297372e52ed19f229ec`, private-desktop deny-all network harness and results trace. Each archive under `../private/native-player-20261008a/probe-output-N` retains `scene-events.jsonl`, exact bundle, native run/verification and input receipt; `plan-N.json` binds source/binaries. No historical failures were overwritten.

Command prefix from workspace root:

```powershell
python tools/raid-lab/native-player/run_trial.py N mechanics --request tools/raid-lab/native-player/mechanics_request_snapshot.json --trace-mode results --control-mode MODE
```

| Trial | MODE / extra option | Outcome and what it established |
|---|---|---|
| 108 | observe | Failed class lookup before battle: bridge needs `.nested("PartsData")`, not dotted nested-class name. Corrected this and nested EReason together. |
| 109 | observe | Complete original 180-second fight; native QTE and parts observed. Exact numerical result equals baseline 104. `passive-result-comparison.json` retained. |
| 110 | probe | Failed at first mode command: Boolean payload helper was local to another function. Defined it in the action adapter. |
| 111 | probe | Complete battle, selection/press/release/cover/restore readbacks. Ten shots but zero new hits while directed aim drifted. This is not a passing aim proof. |
| 112 | probe | Repaired actual competing pointer sampler. Ten shots/ten hits; no shots after release; all five stance 0 and unchanged ammo during cover; firing resumed; auto restored and pointer lease inactive. `tactical-input-verification.json` passes. |
| 113 | kraken-qte | Seven native Break entities hit, no Counter hit events; initial observer lacked preset-end outcome. Kept provisional evidence, then added original event and IsSuccess readback. |
| 114 | kraken-qte | Original preset success at tick 5444; auto restored 5445; complete battle. Native QTE verifier passes. Tick wall 25.229 seconds, fresh host 35.522 seconds. |
| 115 | kraken-qte / `--wall-frame-rate 180` | Same successful QTE, exact numerical result and all observed tactical/QTE events/decisions match 114. Tick wall 32.885 seconds, fresh host 44.104 seconds. Native QTE verifier and `tactical-cadence-comparison.json` pass. |
| 116 | observe | Threat observer works; original result exactly matches104. Initial200-row log cap omitted late attack detail; corrected by focusing log scope on nodes229/230, not rerunning an unchanged broad trace. |
| 117 | kraken-cover-probe | Original squad cover protected Crown from missiles, but released4905 when the last projectile disappeared. Native FireCasting continued; follow-up AoE4965 still damaged characters and killed Naga. This is inadequate cover handling, not a passing full-sequence policy. |
| 118 | kraken-cover-probe | Corrected release condition: native Idle5054 plus no projectiles. Covered4695–5055. Original CoverTakeDamage events route the AoE to all five covers; all five character HP values unchanged over the protected sequence. Complete original battle; explicit post-release ammo evidence added next. |
| 119 | kraken-tactical v1 | Cover/HP/firing-resume validator passes. QTE validator FAILS: newly surviving first-slot Crown MG clears only3circles before battle ends. No Counter hit. Replaced slot-first choice with bounded SMG/AR/MG priority for group212; retained failed QTE receipt. |
| 120 | kraken-tactical v2 | Combined native cover and QTE validators pass automatically. Five survivors, original damage989785848. Tick wall27.946s / fresh host39.805s. |
| 121 | kraken-tactical v2 / `--wall-frame-rate 180` | Both validators pass; numerical results and all192 tactical/cover/QTE observations/events/decisions exactly match120. Tick wall33.174s / fresh host44.535s. `combined-tactical-cadence-comparison.json` retained. |

Rejected explanation for 111: merely waiting for the focus camera or issuing one aim command cannot fix aim while KeyInputContext samples the physical pointer each tick. Recovered `KeyInputContext.UpdateTick 0x0649EDD0` identifies that writer. The scoped virtual-input boundary fixed native hit results in 112 without changing sensitivity, camera, raycast or battle-state fields.

Exact checks:

```powershell
python tools/raid-lab/native-player/verify_tactical_trial.py tools/raid-lab/private/native-player-20261008a/probe-output-112
python tools/raid-lab/native-player/verify_kraken_qte_trial.py tools/raid-lab/private/native-player-20261008a/probe-output-114
python tools/raid-lab/native-player/verify_kraken_qte_trial.py tools/raid-lab/private/native-player-20261008a/probe-output-115
python -m unittest discover -s tools/raid-lab/native-player -p test_verify_tactical_trial.py -q
node tools/raid-lab/native-player/test_kraken_qte_policy.js
```

All pass. Seven input-validator tests include zero hits despite ammo use, continued fire after release, one unit firing in cover, focus drift, active pointer after restore, and missing terminal. Six policy tests cover Counter priority, reaction/settle time, target loss, unsupported groups, failed preset and ownership restoration. Syntax checks passed for changed JS/Python. Detailed evidence has input/bundle/log hashes; no full-accuracy claim.

Final tests:9request tests,7input-verifier tests,7QTE-policy tests (including MG-versus-ready-SMG selection),5cover-policy tests. Cover tests preserve the117 early-release regression and check reaction, unrelated nodes, stale projectiles and unresolved missiles. All28pass. Added native `verify_kraken_cover_trial.py`; latest runner automatically checks QTE and cover for `kraken-tactical`, not merely completed battle. Commands119/120/121 use the same prefix above and `--control-mode kraken-tactical`;121 additionally uses `--wall-frame-rate 180`. Five in-memory negative evidence controls reject native-QTE failure, Counter hit, release during casting, lost character HP and absent resumed fire; receipt in119.

`python client-decompiled/scripts/preservation.py check` after121 returned `unchanged:true, changed:[]`. No native process remains. App `git diff --check` showed only line-ending warnings, no whitespace failures; no commit/staging/server restart. Archived120/121 bundles are authoritative; subsequent workspace edits only clarified comments and comma placement, with syntax checks, and did not change runtime behavior. Installed game, catalogs, hooks, profile/account and preserved original sources remain untouched by this work.

## Next focused work

Continue from combined121, not the earlier input feasibility or missing-pointer hypotheses. The node230 missile/follow-up-cast cover is now native-tested. Do not release solely on missile despawn:117 proved that unsafe,118–121 verified waiting through FireCasting until Idle. Original cover consumes HP and can be destroyed; no invulnerability or reset is injected. Independent per-character cover is not a proven player control. The separate break-collider event at79.332seconds is not this telegraph.

Other QTE groups, charged weapons, unsafe spread/overlap cases, target-preservation rules, other boss staging, complete equipped-build conversion, omitted mechanical dependencies, normal-game parity, and native production search remain incomplete. Do not relabel a passing group-212 test as a complete all-boss controller. Speed remains secondary to reliability.
