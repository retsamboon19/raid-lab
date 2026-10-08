# Repository rules

- Never create a new branch for GitHub work. Make commits and push updates on the existing branch (currently `main`). Do not create feature branches, temporary branches, or branches for pull requests.

## Raid Lab objective — user clarification, October 8, 2026

This requirement overrides earlier Raid Lab investigation next steps in these notes.
The user wants NIKKE's combat MECHANICS implemented in Raid Lab for fast,
results-only simulation and accurate comparison of teams and builds. Required
mechanics include damage, skills and interactions, buffs/debuffs, burst timing,
targeting, boss behavior, RNG and other rules that affect numerical outcomes.
Decompiled code is evidence for implementing and validating those rules.

The user did NOT request gameplay, battle playback, rendered battles, a recreated
game client, or visual completeness. Do not resume normal scene, graphics, art,
locale or presentation restoration as a Raid Lab objective. Earlier trials are
research history, not an instruction to finish that work. Every implementation
or diagnostic must directly improve or validate simulation mechanics/results.
Only retain an asset dependency when its specific effect on mechanics is established
(e.g. hitboxes, projectile collision or timing); cosmetic completeness is irrelevant.

If the objective or a proposed dependency makes the scope unclear, ASK the user
before expanding the investigation or spending tokens on it. Do not substitute
an inferred gameplay objective for the explicit mechanics objective. Keep work
bounded and reuse existing evidence; do not equate decompilation, native startup,
or partial fixtures with verified full mechanic accuracy. The user should not
need to repeat this requirement. All three subagents were stopped after the
budget/scope complaint; do not silently restart the prior investigations.

Latest results-only implementation (October 8): see
`tools/raid-lab/RESULTS-ONLY-SPEED-20261008.md`. Fixed target omission in buff
cache keys and sped up fixed buff contributions with live expiry checks. The
three-candidate benchmark fell from 13.525s to 11.293s with identical full results;
6 focused tests, 33 snapshots, doclint and 76 app tests passed. Full mechanic parity
remains unverified. Preserve existing formation/search edits and this optimization.

Full-engine clarification (October 8): the user explicitly reconfirmed that the
objective is importing/implementing the game's entire combat system from recovered
code, not merely adding a damage calculator. Arithmetic/rounding are component
steps only. Track actual production wiring and native validation separately in
I:/Raid Lab/tools/raid-lab/RECOVERED-BATTLE-ENGINE-WORKLOG.md. Never present partial
native routines, full decompilation coverage, or faster approximate outputs as
completion. The user authorized continuing this work; earlier stopped graphic
investigations remain stopped. New bounded mechanics-only native work is authorized.

Latest recovery status: private mechanics trial49+ initializes original battle
settings correctly. Trial53 reached an original terminal result but had zero boss
HP and zero damage; its retained report is explicitly rejected by encounter-review.json.
The harness now rejects absent bosses (10 mock contract cases pass, not battle parity).
Trial57's private-process tint-only boundary passes original loader awaits/events;
original Monster/Summon/QTE controllers load, corrected Camera-One/Overlay aim binding
passes. First original spawn event occurs after3ticks, then child exits0xE06D7363.
Latest64 native tracing locates the original fault in FunctionUtil.RemoveFunctionFx:
missing FX presentation is looked up before testing an empty FX dictionary. Next
repair isolates that empty cleanup; preserve original function-removal mechanics.
Dynamic spawn hooks at60-63 caused their own heap execute faults and are disabled.
Trials55-56 rejected an
ineffective context.pc redirect; do not repeat it. No valid native boss battle or
parity result exists, and this host is not connected to production search. Do not
load cosmetic services. Unity frame/animation clock parity remains separately open.
Resume tools/raid-lab/RECOVERED-BATTLE-ENGINE-WORKLOG.md and the research workspace
FULL-ACCURACY-WORKLOG.md; do not resume the historical visual scene trials.

Latest user sequencing: implement original NIKKE auto-targeting/auto-aim first
with the remaining headless battle integration. Improved aiming for QTEs and
required parts is a separate follow-up, not part of the original behavior baseline.

Latest67-68 overrides earlier next-step status: private67 produced original populated boss result (695274514damage, bossmax5394000000, 13.772s tickwall), but same-seed68 diverged and stopped on dynamic QTE audio. No repeatability/parity or production integration yet. Existing original PrefabControl supplies only FX cleanup parent; original live cleanup/key removal passes. Next source-backed fixed Unity frame cadence is required: Kraken131colliders are under Animator; batched ticks alone are insufficient. Do not restore sound/graphics services; source-bounded sound-output boundary retains QTE mechanics. Resume latest worklog and KRAKEN-COLLIDER-CLOCK.md.

Latest72-73: original boss fights producepositive results at~10.97s for163.747sbattle. OneUnityframe/tick + captureclock and exactoriginalAnimator denominator adaptation fixes sampledpose nondeterminism (36samplesexact). Same-seedresultstilldiffers ONLYNaga8017damage; fourothers exact. Next74 per-Naga nativehittrace andaim/camera clock audit. Do not claimdeterminism/fullaccuracy/nativeproductionintegration. Currentresearchhelpers/evidence inFULL-ACCURACY-WORKLOG.md andFRAME-SCHEDULING-PLAN.md. Sound-output boundary retainsQTE, noaudioresourcesrestored. NativeRosterCount is notsurvivorcount; useoriginalIsAlive.

Latest74-77: wall-cadence negative control isolates only Naga hit599/tick1421 (53451vs61468). Range trace77 sees pellet4 depth25.00985, original ratio10000; below25 ratio13000. Diagnostic bounds API failed, fix then78/79paired runs. Live Brain manualmode3 rules out double LateUpdate. Preserve failed reports; no fullaccuracy or productionnativeintegration. Resume latest FULL-ACCURACY-WORKLOG.md.

Latest82/83: camera clock rootcause repaired with originalCinemachine CurrentTimeOverride controlledrelativeclock; same originalRNG/sway/gains. Differentwallcadences nowmatchresult1144Nagaevents,32aimsamples,36poses,10rangechecks. Fullparity/productionnativeintegrationstillfalse. Next201characterGetBulletModelnulls need exactoriginalbulletprefab/collider audit; missingCharacterPrefabController source path. Firstuserinputbridge beingbuilt inresearch only. Resume latestworklog; do notrerun prior clockdiagnosis.

Latest90: originalUniTaskPoststartupqueuepass, originalCrown barestatbuilder399/400validated; request84baseline+85/86changedinputpass. Results-only87=10.123s for163.747s (~16.18x;18.781sfreshstartup). OriginalSBSbullet hasNOcollider; all201/235characterprojectiles areSBS: do notfakecollider/restorecharacterart. Nextfullmechanicsgap actualSkillDirector event lists0; c225_skill1_3 fires34times andhasshake marker. Bare5-character inputmode pending. Userbuildconversion,remainingmechanics,normalgameparity,warmreuse andproductionsearchnotcomplete. Readlatestworklog.

Latest trial 91: all five original bare-build calculations were applied and read back correctly, then completed the original 180-second battle. Only explicit empty equipment/cube/favorite/research and bond 0 are supported. Original snapshot conversion for equipped builds is next. Empty skill director lists are created upstream of SkillDirector; inspect live timeline/FX gates, not cosmetic reconstruction. Production Raid Lab still uses Python; full mechanical parity and native search integration remain incomplete. Resume the latest worklog.

User priority update (October 8): approximately 10 seconds per battle is acceptable for now. Prioritize reliability, consistent native runs, remaining mechanical dependencies and correct build conversion. Hold further speed/warm-reuse optimization. Original battle code is running only in the private native harness; production Raid Lab search is still Python. Trial 92 completed, but comparison to 90 failed with the first Naga damage at tick 9 vs 16, before the new timeline snapshot at tick 199. Do not assert the diagnostic caused it; source-bound startup/first-shot state comparison is next. The actual timeline GameObject and PlayableDirector are valid; original FXController is absent.


Latest reliability checkpoint (October8, trials92–107): exact archived90 replay97 also gives the newer first-hit/result, ruling out the new observer/stat-refactor source as the historical drift cause; do not repeat those negative controls. Bare original CharacterSnapshot constructor/converter is now applied to all five fighters. Empty cube is a zero-valued nonnull sentinel; Nullable<TableType> needs validated8-byte native payload; three optional favorite-skill override pointers must be null for bare builds. 102 failed only on Array logging metadata; fixed with `.object.class`. 103/104 complete and match with diagnostics on/off; 101/103 also match result/hits/poses. Varied slots/levels/skills/seed105 passed; 106 hit the unchanged35s diagnostic guard; 107 results-only at the same180FPS wall cadence completes and exactly matches105. Keep failed106 evidence; do not claim it passed. Native receipts103/104/105/107 verify five converted objects and original results. Full accuracy/normal-game parity and production native search remain incomplete. User accepts earlier~10s benchmark and prioritizes reliability; hold warm reuse/speed. Production gear/Overload source preservation is being integrated; resume latest worklog and SOURCE-INPUT-CONVERSION-NEXT.md, not stale trial64/90 next steps. Installed game/account unchanged; no native process remains.

Product reliability update: local Raid Lab import now preserves per-slot gear IDs and individual Overload effects in sourceProvenance, bound to character/build/content hashes. Edited or incomplete sources are explicitly invalidated/omitted without changing calculator behavior; browser integer serialization is covered.57focused/roster/account tests pass. New helper/test files have explicit .gitignore exceptions; no staging/commit/server restart/account migration. Native equipped-build conversion is still next, and production search remains Python. Latest detailed notes include trial103/104 and105/107 exact-result matches plus failed diagnostic106 time limit; do not conflate those with normal-game/full-mechanic parity.


Latest user steering: assess smarter tactical automatic play FIRST (required parts/QTEs, cover/resume) for boss consistency. Feasibility completed source-only; see research native-player/SMART-AUTOPLAY-FEASIBILITY.md and ACTIONS/OBSERVATIONS companions. Original command and observation paths exist, but auto-aim ownership versus manual fire-release is unresolved (0x064A6CE0 vs0x064602F0). Prove that control sequence and live QTE/telegraph timing before implementing a boss controller; no naive auto-off/down/up claim. Retain original-auto baseline, native battle mechanics and results-only scope.21Python/data encounter profiles do not mean21native bosses; native latest107 remains unchanged. No runtime modification or new native run during feasibility. Reliability priority persists.

### Native tactical implementation authorized — October 8
The user authorized implementation after feasibility, with efficient bounded diagnostics. Added separate original/observe/probe controller modes to the private research harness; staged bundle and request receipt identify the mode. Original automatic combat remains the baseline. New adapters only observe live original state or issue original player commands; no damage/outcome injection or installed game/account edits. Source inspection resolved manual release through TeamContext.OnGetInputEvent (InputPointUp ID74000 -> CheckChangeStanceEvent stance0), independently of the auto-only BT branch. Input proof still requires native readbacks. First trial108 uses passive observation, results trace, original snapshot request; it distinguishes native observation/bridge compatibility before command effects. Continue from SMART-AUTOPLAY-FEASIBILITY.md and the latest FULL-ACCURACY-WORKLOG.md. Production Raid Lab native search and full accuracy remain incomplete.

Native autoplay checkpoint (October 8, through115): implementation authorized. Read native-player/SMART-AUTOPLAY-IMPLEMENTATION.md before further investigation. Original input proof112 passed actual shots/hits, release, all-five cover/ammo stop and auto restoration. Drift111 was caused by original KeyInputContext physical mouse polling; exact-callsite virtual pointer fixes it, without battle-state writes. Kraken group212 reactive QTE policy114/115 hit all7Breaks, noCounterhits/observedHPchange, original PresetEnd Success=true and native IsSuccess, then restoredauto. Differentwallcadences match numericalresults/QTEobservations/events/decisions. Preserve failed108 nestedclass/110boolhelper and inadequate111 aim evidence; do not repeat fixeddiagnoses. Native latest115, no process left. Next targeted cover investigation: node230 Shot02 skill532033 projectile lifecycle and cover-vs-character native damage; only whole-squad cover is proven. Production search remainsPython, otherbosses/equippedbuilds/parity incomplete. Updated scopes/evidence/tests in detailed note; no installed game/account modifications.

Latest native tactical checkpoint (October 8, supersedes115 next step): combined `kraken-tactical-v2` passes120/121 at default/180 wall FPS. Both original cover and QTE validators run automatically. Cover4695–5055 protects all5 through node230 missiles plus follow-up AoE; original CoverTakeDamage routes blast to covers; characterHP unchanged, original firingresumes. QTEgroup212 all7Breaks hit, noCounterdamageobserved, nativePresetEnd Success/IsSuccess at5438, auto restored. All192tactical observations/events/decisions and numericalresults exactlymatchacrosscadences.5survivors vs3baseline, damage989785848 vs1017313717 (~2.7%lower): conservative survivalpolicy, not damage-optimal. Preserve117 early-release inadequacy and119 failedQTEreceipt (first-slotMG too slow); v2prefers readySMG/AR/MG and keepscoveruntilnativeIdle plus projectile resolution.19new focusedtests +9requesttests pass. Sourcepreservationunchanged, no playerleft. Exactarchive121/cadencecomparison and SMART-AUTOPLAY-IMPLEMENTATION.md are currentresume points. Next122 ifanothernative trialneeded. Otherbosses/groups, repeated/overlappingphases, completegearconversion/parity/productionintegration stillpending; productionsearchremainsPython. No installedgame/hook/catalog/account edits. Do not repeat resolvedphysicalpointer/input-release or obsolete113 outcome diagnostics.
## Autoplay scope correction — October 9, 2026

The requested scope is smarter automatic play across ALL Raid Lab boss fights:
required-part and interruption targeting, boss-specific mechanics, dangerous-attack
cover and reliable resumption, using original battle mechanics with results only.
Kraken trials120/121 are the first validated case, not completion or permission to
stop at one boss. Inventory the actual selectable encounters, bind each native
encounter and policy to original sources, and validate the affected fights.
Do not describe generic code, mock tests or Python profiles as native boss coverage.
Current production search is still Python; native integration remains required.
Research records: I:/Nikke offline/tools/raid-lab/native-player/
SMART-AUTOPLAY-IMPLEMENTATION.md and BOSS-AUTOPLAY-COVERAGE.json as it is built.

Latest checkpoint123 (October9): reusable `boss-tactical-v1` passes native QTE
and cover checks on the existing Kraken fixture, with the same full numerical
result as120. Failed122 is retained; it exposed zero-based collider IDs, native
preset/group identity, consumed attack-history eviction, and sampled-vs-native
condition time errors. All corrected with focused regression coverage. Mirror
source assets are staged and schema2 encounter input prepared, but no native
Mirror fight has run. Next124. Publication snapshot is
`tools/raid-lab/research/native-player`; it is research source, not the production
backend. The user requests pushing all progress to the existing GitHub main branch.
