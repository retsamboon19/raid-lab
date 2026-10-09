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

## Current continuation — all bosses, October9, through127

This supersedes the121 next step above. The user requires all Raid Lab boss fights,
results only, with original battle mechanics and smarter required-part/QTE/cover
inputs. Kraken is the first validated case. Production search remains Python.

Generic `boss-tactical-v1` passed native123 on Kraken after failed122 exposed
zero-based collider IDs, preset/group identity, attack-history cursor and original
condition timestamp issues. Result equals120 exactly; all7Breaks, cover4695–5055,
resume and five survivors pass. Exact receipts remain in probe-output-123.
Public GitHub main checkpoint cd9d652 contains source progress through123.

Source inventory is BOSS-AUTOPLAY-COVERAGE.json; the current ten Intercept profile
registry is source-verified, not ten validated native fights. Prepared requests
are Mirror/Ultra level400 and Special Chatterbox level200. Three reviewed manifests
can use the shared mechanical hierarchy, with exact profile/geometry/chunk binding
in mechanics_profile_binding.py; other profiles still fail the staging gate.

Mirror original-auto observation attempts124–127 are all failed precombat trials:
124 exposed an obsolete Kraken-only FX geometry guard (fixed with exact common
hierarchy plus encounter hashes);125 a dynamic death-effect bundle omitted from
static Addressables closure (source-verified staged32chunks);126 exact monster
SpotEffect and per-skill serialized references (source closure staged213chunks);
127 four concurrent shared default Energy skill resources. The latter loader
fallback closure is the current repair. Do not rerun unchanged127 or describe it
as a completed fight. Exact commands/results/hashes are in FULL-ACCURACY-WORKLOG.md,
MIRROR-DYNAMIC-EFFECT-TRIAL125.md and MONSTER-RESOURCE-CLOSURE-TRIAL126.md.

Generic modes now observe original SpotMonsterBreak collider state and events.
Candidate Mirror policy uses live enabled positive-HP Break colliders only,
original input commands and bounded reaction time; QTE/cover have priority and
release the required-part input lease first. Native targeting/cancellation is
unverified. Ledger/controller/policy/priority synthetic checks pass; the native
verifier requires actual press, Hurt and HP decrement, with interruption reported
separately and no unsupported skill520676 attribution. Do not treat mock tests or
source-backed collider centers as proof that shots hit.

INTERCEPT-MECHANICAL-INPUT-AUDIT.md found no missing battle setter for CoverStageLv
or AutoChargeId. Original cover uses constructed character level and its native
cover table; Special requests already match original level200. Full account
snapshot correction, Anomaly below-cap parity and equipped builds remain pending.
The unrelated existing user game PID18840 must not be attached to or stopped.

## Current continuation through133

This supersedes the127 load failure. Mirror128 original-auto and129/133 candidate
tactical fights complete in the original engine. Candidate shots reach Break01,
but all observed Liter/Crown Break damage is zero and HP stays350000; tactical
verification FAILS. Correction after133: positive inner GetDamage samples hit
different, non-Break colliders; no post-calculator zeroing was established.
MainHP immunity is false for sampled inner hits. Correlate the outer GetDamage
call and original early-return gates with the same Break collider; do not guess from boss
element or retry the same firing policy unchanged. Positive Hurt and HP decrement
remain mandatory. New decision-bound snapshots fixed stale-state evidence pairing;
21 verifier regressions pass;123 remains a read-only passing control.

Chatterbox130/131 missing mechanical skill dependencies are source-staged and132
completes an original fight with all five native input readbacks and clean exit.
It wipes in34.1885s; the first hit87 precedes first MonsterAttack197. Earliest
FireCasting4 plus original TimelineSkill branch is the next cover discriminator.
See CHATTERBOX-TACTICAL-RULES-TRIAL132.md; cover interception is not yet proven.
Ultra static/monster closure is prepared for its first observation trial134.
No installed game/account changes. Production Raid Lab remains Python.

User stop boundary: at5% main allowance remaining, stop engineering and agents,
update/verify GitHub main, then shut down PC without force-closing applications.
Latest checked23% remaining before134; preserve enough allowance for publication.


## Cross-boss checkpoint through140

Four bare fixtures now complete original-engine executions: Kraken, Mirror,
Chatterbox and Ultra. Only the recorded Kraken sequence has passing tactical
coverage. Ultra139 has0nativeerrors, valid inputs and clean exit:2322ticks,
76.5273s battle,14.639s tick wall,0survivors. Three original Break episodes fail;
first is three live280000HP Break04/05/06 targets. See ULTRA-FIRST-BREAK-TRIAL139.md.
Do not count absent QTE phases or baseline execution as tactical success.

Mirror138 paired same-call inner/outer damage now confirms positive damage for
actual Break819201, while the later event remains0. Source constructor and
processing need object-identity tracing; the earlier133 post-calculator inference
was unsupported and remains corrected.141 will trace the three result stages.

Chatter137 failed an observer assumption (one nested skill getter observation).
Source-backed retained skill-list read now replaces that assumption, with native
node/skill/pass-time checks and5mock tests.140 expired during earlier startup,
BEFORE this observer was installed, so it cannot judge the repair or coverability.
Exact entry/release squad HP and resumed-ammo captures plus strict verifier are
implemented; real cover interception is still unverified. Startup context-race
repair has4behavioral regression tests; unrelated errors are never retried.

The user cutoff remains5% main allowance remaining: stop, publish verified
GitHub main checkpoint, then request normal PC shutdown. Production search still
uses Python; full equipped builds, complete boss tactics and parity are unfinished.


## Checkpoint through trial149 (October9)

Chatterbox148 passes the strict first-attack cover verifier: original node6 /
skill510209 at4, cover5, impact87 hits cover268587008 while target4098 HP474573
remains unchanged, original PlayEnd197, release198, firing resumed203. Original
1741tick result, five input readbacks,0nativeerrors and clean exit24.067s. This
is one diagnostic episode only: team still wipes; no full Chatterbox policy or
boss-win claim.146 had fixed the shared-variable path but failed a nested-hook
assumption;148 binds GetSkill to original return RVA0x0654892A and retains a
copied pointer. All earlier failed reports remain immutable. Six probe mocks
and seven strict-verifier mocks pass.

Mirror149 completes1339ticks/inputPASS/0nativeerrors/cleanexit27.235s, while
required-part tactical verification still FAILS. Correct low-byte native bool
readback now establishes original ImmuneDamage37=false and
ImmuneOtherElement110=true on weak-element mismatch [500001] versus[200001],
with original immunity tuple[0,1,1]. At1127/1129/1131 these coincide with the
three retained Break819201 results changing11525 to0 in CommonHurtEvent.Send.
Weak-element match[400001] at1132 yields tuple[0,0,1].115/115 condition rows and
21/21 result rows retained, no fault or active hook stack. This establishes the
active original elemental immunity branch. Next implement shooter eligibility
using live original element/function observations, then prove positive damage,
BreakHP loss and interruption. Do not bypass immunity or hard-code a boss-wide
element rule.147's unmasked HasFunction booleans were invalid high-register
bits; preserve its report and correction, never cite those booleans as evidence.
Native bool hooks must read AL, not treat the whole return register as boolean.

Exact final commands (workspace root):
`python tools/raid-lab/native-player/run_trial.py 148 mechanics --request tools/raid-lab/native-player/mechanics_request_chatterbox.json --trace-mode results --control-mode boss-tactical`
`python tools/raid-lab/native-player/run_trial.py 149 mechanics --request tools/raid-lab/native-player/mechanics_request_mirror.json --trace-mode results --control-mode boss-tactical`
149 plan8e1da5187cf4ecdeaa152bb3eb4d00bb4b16328c02f65bc889b54d5be15da65c,
bundle1e7bdc9d1ba9cf6ce7b78ded04952b918aa1ee154cf98b32a472139209a9654c;
148 plan6a2db20a4dae5b70a9f49fb5647322f750371cde079d0d41e896e9a05d9e50e6,
bundleb3c80ec8d73eea742e9a25dc380c34398db9c9a0765b97a6ac95487642e33058.
Source-only GitHub checkpoint includes successes and explicit failures; actual
native receipts/resources remain private and hash-referenced. Four bare boss
execution fixtures, one Kraken tactical sequence and one Chatterbox opening
cover episode do not prove all-boss tactics or full mechanics parity. Production
Raid Lab search remains Python; native equipped builds and integration incomplete.
