# Character kit coverage

The catalogue contains 202 real characters. All have executable definitions for
Skill 1, Skill 2 and Burst, including each available Favorite Item replacement.
The initial coverage update added 113 missing kits; the September 20 refresh adds
Guilty: Mighty Bunny and Sin: Swift Bunny. Internal engine test characters
are excluded from the app catalogue.

Skill support means that a character can participate in simulation and team
search. It does not mean the model has been calibrated against an in-game run for
every character, investment level and boss.

The [September character update](CHARACTER-UPDATE-2026-09.md) records source checks,
new Bunny Mode controls, verification, and remaining limitations.

## Data and implementation

- `tools/nikke-team-builder/scraper/nikke_scraped.json` remains the sole canonical
  skill-text and level-value source. No level interpolation is used.
- `runner/complete_roster.py` compiles 108 of the additions from explicit reviewed
  rules and canonical values. `data/skill_cooldowns.json` supplies cooldowns from
  native `CharacterSkillTable.SkillCooltime / 100`, matched by resource name.
- E.H., Emma: Tactical Upgrade, Eunhwa: Tactical Upgrade, Vesti: Tactical Upgrade
  and Guillotine: Winter Slayer use the MIT-licensed
  [upstream skill definitions](https://github.com/Jgaram/nikke-calc/blob/ea82f7691a6bfb9de28689ef5078046040a8747f/data/parsed_skills.json).
  Their required gauge-boundary, formation, non-core-hit and ammunition mechanics
  are included. Tactical formation effects switch off when their caster falls.
- K's burst uses native shot 1004102: 144 rounds/minute, two muzzles with five
  pellets each, and a 999-round magazine. Summer Neon's burst uses shot 1001402:
  a seven-round launcher at 90 rounds/minute with a 2.5-second reload.

The shared engine now handles received-hit triggers, shield depletion and repair,
decoys, next-shield bonuses, healing modifiers and stored excess healing, cover
repair/revival, damage sharing, revives, attack/HP copying, damage accumulation,
charge-hold counters, and interruption/projectile damage bonuses. Shared shields
have one finite HP pool; damage sharing cannot redistribute recursively.

Incoming boss attacks can defeat individual characters. Fallen characters stop
acting, healing targets exclude them, and revival can return them to combat. A
squad wipe stops the run. Final survival reports still fail if a unit remains down.
Special Interception also stops on its maximum reward threshold.

Existing enemy ATK debuffs now affect incoming enemy attacks instead of reducing
player ATK. Stack removal reaches the specified allies and can consume the last
stack. These corrections explain the reviewed changes to six local regression
baselines; the remaining damage baselines are unchanged.

## Verification

Run from `tools/raid-lab` using the bundled Python:

```
python validate_roster.py
python -m unittest test_complete_roster -v
python -m unittest discover -s . -p "test_*.py"
```

The catalogue validation covers 530 simulations: every character at skill levels
1 and 10, plus all Favorite Item stages. These are synthetic 45-second checks for
data compatibility and finite output; they do not prove every conditional skill
activated. Behavioral tests separately exercise shield pools, damage sharing,
revival, health thresholds, Kilo's branches, cleansing, accumulation, formation
conditions, experience levels, ammunition scaling and stack consumption.

A team containing Liter, Ludmilla, Maiden, Crow and Rapunzel was also run against
each of Alteisen, Gravedigger, Blacksmith, Chatterbox and Modernia. This checks the
connection between newly supported kits and each Interception EX encounter; it
does not assert that this team can clear them.

Engine maintenance gates remain `python -m runner.doclint` and
`python -m runner.snapshot` in the engine workspace. Baselines are regenerated
through the snapshot runner only after reviewing a change's cause.

## Model limits

Budget-focused corrections, 24 September 2026:

- Delta: Ninja Thief's IFAK now accumulates healing received during its window,
  caps it using her effective ATK and applicable capacity bonus, then heals
  living allies when the window ends. Each window has an independent reserve.
- Ade: Agent Bunny's optimal-range conditions and normal-shot bonus now share
  a distance check where encounter positions are available. Her range extension
  uses a documented near-boundary approximation; unknown distances retain the
  existing explicit weapon-range setting. This is not exact collider targeting.
- Additional piercing range and precise area overlap remain outside this pass.

Validation: 77 targeted checks passed. The Delta/Crown snapshot gained 2.32%
team damage because IFAK now triggers Crown's healing-received team buff; its
reference was regenerated with the snapshot runner. The other 32 snapshots
were unchanged. Document/data lint passed after updating the effect statuses.

Boss positions and scripted actions remain fixed. Blast-radius overlap, additional
piercing range and pulling movable enemies are not spatially simulated. Movement
and crowd-control effects cannot move or stun a scripted boss. Enemy shield damage
bonuses apply to hits classified as shield hits; elemental immunity barriers are
not finite HP shields. Hit-count interruption circles still require their stated
number of hits regardless of damage bonuses.

Incoming attacks, aiming, collision geometry and execution remain an experimental
physical model. All catalogue characters and Favorite Item stages have executable
definitions; this does not establish complete implementation of every effect.
Spatial range and piercing effects remain particular limitations.

For Snow White: Heavy Arms, a charged shot now retains the enemy locked at its
firing boundary for Auto Fire 2 even though its `on_attack` callback clears Lock
On before `full_charge_fire` is dispatched. The recipient snapshot lasts only
for that shot's callback. The native ordering of these two callbacks has not
been verified; the correction addresses a zero-damage artifact in the simulated
Indivilia run, not full score parity with the native client.
