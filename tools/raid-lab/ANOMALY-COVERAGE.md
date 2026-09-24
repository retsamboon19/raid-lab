# Anomaly Interception acceptance requirements

User requirement, 2026-09-20: complete all remaining Anomaly bosses (Ultra,
Harvester, Indivilia, Mirror Container), including every phase, part, interruption,
attack effect, incoming damage, cover interaction, summon and projectile. This is
a required completion gate. Merely executing a 180-second script is insufficient.

Acceptance revised by the user, 2026-09-24: prioritize sufficiently useful team
recommendations within the remaining usage budget, rather than exact client
parity. The four detailed models are available for that practical use. The
unresolved fidelity items below remain visible; no full-fight equivalence or
precise damage guarantee is claimed.

Latest verification findings (2026-09-24):

- Finite behavior-tree repeaters now preserve the final child's status, and
  ParallelComplete returns the first completed child's actual status. Native
  control-flow regressions cover failed phase-cycle completion and cancellation.
- Indivilia's native owner-attributed score is 1,238,268,419: 1,162,203,879
  against the main boss and 76,064,540 against summons. Attribution matches all
  five character score getters at every one of 19 captured snapshots.
- The saved build differs from the active native equipment effects. A private
  diagnostic omitting overload and collection effects matches all five native
  ATK values at seconds 1 and 10 within one point and four of five ammo limits.
  Production equipment handling is unchanged; this diagnostic is not a claim
  that those effects are absent in normal gameplay.
- Nayuta's infinite-ammo display and true maximum now match native 999/999/493
  using her installed temporary weapon's explicit 999-round base. Other
  unlimited replacement weapons retain their own backing-magazine rules.
- Indivilia now starts at its recorded native spawn origin, point153, avoiding
  a spurious opening return jump. Its jump waits for the start and landing
  animations, and Shot01 includes the measured 0.8-second runtime casting delay.
- With the corrected behavior tree and matched diagnostic equipment effects,
  an intermediate Indivilia diagnostic reached phase two and dealt 1,336,815,568 direct boss damage versus
  native primary-boss-attributed 1,162,203,879 (about 15% higher), with 13 versus
  14 full bursts. This preceded the latest spawn/jump/casting corrections and
  is an unmatched diagnostic, not a current accuracy score or parity pass.
- Remaining measured discrepancies include a forced squad-wide mid-clip reload,
  boss casting waits and jump completion. Historical totals below precede these
  corrections and are not current accuracy results.

| Requirement | Acceptance evidence | Status |
| --- | --- | --- |
| Correct installed content variants and stage thresholds | Freshly decoded installed 152.8.11 static pack; all 701 selected records match the model | Verified; the original 151 pack hash and current verification hash remain distinct |
| Every phase and success/failure branch | Behavioral traces at each stage, with real interruption hits and misses | Native phase clock/callback implemented. Corrected CheckPhase's continuation guard: native Success=2 below the threshold, latched Failure=1 on reaching the stage threshold or falling strictly below the HP threshold. Regression now checks branch polarity, not merely that both outcomes occur. Full-fight branch verification remains in progress |
| Finite parts, replacement HP and separate break bonus | Native arithmetic and per-lifetime regressions | Implemented and tested, including Mirror HP group expiry/replacement and Ultra separate core/chamber hits |
| Mirror first-hit closure, hit-count cancellation and DEF layers | Native passive/function records plus behavioral regressions | Implemented; actual tree tests cover destruction flags, repeat routes and HP-cycle progression |
| Ultra core shell, poison, chambers and interruption patterns | Source asset timelines, damage-effect traces, positive/negative checks | Hidden-core pierce, finite core HP, guide-supported chamber overlap and integer poison ticks implemented; animated collision verification remains open |
| Harvester summons, overflow attack, head and missiles | CallingList, add AI and source geometry; lifecycle regressions | Native gravity/drop integration and teleport/braking sequence implemented against measured spawn events. Missile target identity is locked and its stance position sampled at each launch. Animated muzzle and exact landing collision verification remain open |
| Indivilia pincers, tail, transition, fixed-slot attacks and Blade | Exact source branches, targeting and collision behavior | Source branches and attacks implemented. Summon return movement remains inside SpawnAction; outer adds' 3.917-second gate and subsequent AI path match live observations. Authored wave_combat_zone and native pyramid membership now determine the inner gate, predicting about 4.74 seconds with ±0.04-second onset uncertainty pending live validation |
| Red/grey target graphs and elemental checks | Actual QTE records, activation/expiry/counter-hit tests | Root preview delays, shared native deadline and barrier-only element restriction verified; all four prefab box dimensions, ColIndex bindings and root z=16 offsets recovered. Six live Indivilia SetCollider observations confirmed root placement. World positions/lifetimes integrated; animation bindings affect visual effects only. Native center-pellet/chord spread sampling, per-pellet ray contacts, impact-centered RL splash, misses and accidental grey hits integrated and tested. Installed replacement geometry now covers 20 characters/24 shot rows when a unique physical mode can be resolved. Dynamic camera/aim origins, projectile travel, distinct or multi-target weapon modes and incidental follower contacts remain open |
| Distinct ordinary and special interruption DEF | Native BreakCol and SpotQuickTimeCollider constructors/getters | Special QTE copies base DEF; ordinary BreakObject uses body DEF including normal StatDef layers; both tested |
| Cover-specific hurt functions | Original `IsValidStatusCondition` on character and cover entities | Native verified: IsCover=1 means character, IsCover=0 means cover |
| Elemental stage damage multiplier | Original numerical function and passive dispatch | Native verified: stage passive dispatch produces 30000/40000/50000; advantage multiplier is 4/5/6 |
| Character versus cover elemental damage | Original target entity element lists | Native verified: cover has no elemental code and does not inherit its owner's elemental disadvantage |
| Volleys, projectile HP and projectile damage | Separate legacy and timeline dispatch traces plus original numerical damage function | Physical counts, disabled/destroyed launcher filtering, coefficient rounding and distinct bullet/projectile divisors implemented and tested |
| Projectile launch snapshots | Native FireData and projectile caster-data construction, plus stage-change regressions | Legacy volleys snapshot DEF once at volley start; each launch snapshots its own ATK, stage multiplier and projectile HP |
| Pending volley cancellation | Native MonsterContext StopFire, original IL2CPP enum values and ProjectileContext sticky-projectile handlers | Corrected after native enum measurement: scene type 4 is Dead; phase 2/3 preserves scheduled launches. Part destruction cancels only a matching cancelable skill; already launched ordinary projectiles are retained |
| Legacy attack completion | Attack.OnUpdate, FireCastingV2, PlayAnimEnd native coroutine chain and exact controller clips | All 25 ordinary attack rows use physical volley end plus native shot delay and matching animation tail; implemented and tested |
| All-enemy and distributed damage to summons | Native target eligibility, per-target DEF and destruction lifecycle regressions | Native AllMonster predicate verified; Indivilia NoAllMonster summons excluded from damage and split denominator while manually aimed hits remain valid; per-target DEF and QTE-independent skill targeting tested |
| Target-owned enemy debuffs | Independent projectile/special-QTE status, activation-time membership, recipient stack/expiry and immunity regressions | Boss DEF/received-damage/ATK debuffs no longer leak to independent targets; reapplications retain separate recipient windows; ranked damage and same-target routing tested; periodic damage visits each original recipient once and excludes later spawns. Installed v152 skill preference metadata applies native NoneTarget ordering to identified direct skills and exact nested skill IDs. Split skills now select their authored recipient set before dividing damage. Native circle/area base radii, Circle capsule heights and Stigma projectile-layer exclusions are exported; Circle endpoints follow the native forward-axis formula. Ranged selectors accept a physical collider provider; absent that provider, the inclusive fallback is counted in range_targeting_unresolved and remains unverified. Active StatInstantSkillRange adjustment and world collider intersection still need that provider. |
| All-parts skill targeting | Current InstantAllParts enumerator and finite-part destruction regression | Body once plus each living damageable enabled subpart; independent DEF, HP, first-hit hooks and break bonus implemented |
| Per-collision burst gauge and hit notifications | Current MakeShotResultTargetInfos and ProcessDamageTargetInfo calls | Runtime collision/part/core/body counts integrated and tested, including pierce, summons, special interruption targets and all-parts skills |
| Instant, delayed and periodic effects; immunity | Original function dispatch and timing regressions | Poison application, refresh, cadence and all 15 integer damage outputs verified against original functions; cinematic clock ordering tested; remaining effect audit in progress |
| Incoming reduction, minimum and rounding | Current GetDamage native code; original DoubleToLong numerical probe | Generic and elemental reduction rates add; minimum one and half-up integer conversion tested |
| Per-boss cinematic clocks | Exact phase asset isStopTick, native control flow and measured campaign/Spot clocks | Ultra's natural phase at Spot 111.085–114.077 recorded 122 squad fire callbacks and advancing Spot/Campaign clocks. Indivilia's natural phase held Spot at 147.140930, Campaign at 147.046951 and both tick counters unchanged for 8.784 wall seconds, with zero squad fires. Native enum 4 is Dead, 2 is phase. Non-stop phases use ordinary battle time; Indivilia freezes combat. Mirror's phase advanced both clocks by 4.9845 seconds and recorded 186 squad fires; Harvester's authored 1/60-second fixed timeline completed within one observed Spot tick (5 wall milliseconds). All four phase clock policies now have direct observations; same-tick queued fire may drain at Indivilia's pause boundary |
| Movement, phase animation and projectile flight | Extracted paths/timeline callbacks or measured hidden-client trace | Source timeline loops/marker targets and boss movement integrated; Ultra/Harvester/Mirror share independently measured character and cover endpoints, with partial Indivilia confirmation. Mirror/Indivilia projectile defaults now use this formation and separate cover transforms; live overrides remain available. Animated launchers, stance transitions, slot 2's hiding endpoint and remaining projectile/add geometry verification are open |
| Client damage-statistic semantics | Native score getter, component counters and excluded entity classes | Verified: character and squad score sum noncritical TakeDamage.Total plus TakeCriticalDamage.Total. OnTakeDamage excludes SpotDynamicObject and SpotQuickTimeCollider. Summon damage remains part of the native character total and must be separated when comparing direct boss damage |
| Complete modeled fight vs independent client evidence | Matched squad/build/aim/event trace with quantified differences | Complete controlled traces captured for all four bosses; current diagnostic comparisons are below. The clone suppresses squad HP damage and forces QTE success; target accounting, aim and RNG are not yet matched. Per-character/10-second differences and rotation are recorded privately. Native weapons update about 60 times per second, but observed fire counts differ materially from the simulator. Not a parity pass |

Historical controlled diagnostics after the Snow White: Heavy Arms Lock On
target snapshot correction but before the CheckPhase guard correction
(2026-09-24; new comparisons are pending):

| Boss | Native score | Simulated direct boss damage | Native / simulated full bursts |
| --- | ---: | ---: | ---: |
| Ultra | 1,135,805,617 | 2,090,740,170 | 13 / 13 |
| Harvester | 2,206,457,244 | 3,979,825,791 | 13 / 14 |
| Indivilia | 1,235,696,900 | 2,294,778,069 | 14 / 14 |
| Mirror Container | 1,256,626,126 | 3,507,074,872 | 13 / 14 |

These columns have different target scopes and are diagnostic discrepancies,
not calibrated accuracy scores. The native caster score uses each damage
event's aggregate, rather than the sum of its per-recipient damage entries.
Matching target attribution and firing behavior is required before comparing
damage formulas or changing coefficients. The earlier Indivilia diagnostic
(1,761,738,828) preceded the Lock On correction and is superseded by this table.

The user authorized NIKKE Offline testing, with the strict requirement that it
must not steal focus or bring a window to the foreground. Native probes run in
disposable `CREATE_NO_WINDOW` subprocesses and do not launch the game player.
Any graphical measurement must meet the same no-foreground requirement.
The cloned client has now entered a practice battle on a separate Win32 desktop,
with attack, part-destruction and cutscene callbacks recorded. Boss-specific
matched traces remain in progress; this is not yet a parity result.

Private, reproducible evidence lives under `private/anomaly-audit/` and is not
included in the distributable app. Current original-runtime tests record cover
condition results and `GetElementBonusDamage` values (30000 -> 4.0, 40000 -> 5.0,
50000 -> 6.0 when elemental advantage applies). These are isolated method tests,
not proof of a complete battle.
