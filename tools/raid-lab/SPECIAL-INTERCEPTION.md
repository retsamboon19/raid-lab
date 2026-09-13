# Special Interception implementation audit

Reviewed 14 September 2026. These five encounters now execute boss-specific
combat policies. Results remain **modeled outcomes**, not verified game clears.

## Recovered data

`raid-boss-combat-data.json` adds five EX profiles and preserves the existing
14 Museum/Anomaly profiles unchanged. The EX monster is resolved through
`InterceptSpecial.SpotId -> InterceptWaves.TargetList`, rather than a similarly
named raid monster. Archive SHA256:
`D14690756E7E8D24CF13DF50A7DB62A6C932C28E7A759BA6E731FDFCF1E15A5B`.

| Boss | Wave | Monster | Weakness |
|---|---:|---:|---|
| Alteisen | 6302001 | 3520010133 | Fire |
| Grave Digger | 6302002 | 3520020143 | Iron |
| Blacksmith | 6302003 | 1520030113 | Water |
| Chatterbox | 6302004 | 1520020113 | Water |
| Modernia | 6302005 | 3520040153 | Wind |

EX fixes units at level 200 while retaining imported investment. Enemy level
287, cover stage 8, and damage-stage groups 201–205 are taken from those mode
records. The recovered reward thresholds are 0; 8,404,001; 11,641,001;
17,026,001; 20,454,001; 26,539,001; 32,798,001; 46,641,001; and 62,007,001.
Enemy skills, circle HP/cast times, finite part HP and projectile HP are stored
alongside the mode, wave, behavior-tree and animation records.

## Research and implemented policies

The following authored gameplay guides inform the reduced phase policies;
they are older guides, so their team tier lists are not used as current rankings.

| Source | Policy used |
|---|---|
| [Alteisen](https://nikke.gg/special-interception-alteisen-train/) | Right weapons first; separate destructible missiles from green missiles; phase-two circles take priority. |
| [Grave Digger](https://nikke.gg/special-interception-gravedigger/) | Circle failures change drill pressure; later drills pierce cover. |
| [Blacksmith](https://nikke.gg/special-interception-blacksmith/) | Favor recovery, clear bombs, aim at the core, and handle the capture interruption. |
| [Chatterbox](https://nikke.gg/special-interception-chatterbox/) | Preserve the head and one launcher; protect the middle opening slot. |
| [Modernia](https://nikke.gg/special-interception-modernia/) | Focus the core, cover the first laser if needed, and preserve a wing. The second laser supplies the critical part deadline. |

Circle damage is resolved from actual simulated hits, separately from body
damage. Failed checks drive retaliation. Missiles require HP damage. Finite
cover, shields, healing, taunt, stun and corrosion affect survival; scoring
stops at the first death or maximum reward threshold.

EX selection compares boss HP progress, then interruption reliability and
survival margin among completed reward targets. Direct damage remains visible
separately from modeled part-break HP loss. DPS and Full Burst uptime use the
observed encounter time. A route with no circle check is not reported as a QTE
pass. Saved results from older models retain their original evidence.

## Calibration limits

Movement and recovery are reduced to explicit policies, usually one second;
Modernia also retains the recovered opening waits. Missile flight uses three
seconds and aim changes use 0.15 seconds. Exact trajectories, projectile
counts driven by animation, simultaneous splash/pierce hits, cover-stat
conversion and incoming damage need recorded-game comparison. Train turret
enrage timing and manual dodge strategies are not reproduced fully.

Chatterbox's seven-stack death condition comes from the connected function
records. The separate overlap-change operation is approximated as one extra
stack; its client execution still needs verification. Death stops the model,
so revival and continued play with four units are outside its scope.

These limits are material for low-investment teams. The interface and exported
reports disclose incomplete calibration; a green check is evidence about this
simulation only.

## Verification

Run from `tools/raid-lab` with the bundled Python and Node:

```text
python -m unittest test_special_interception test_raid_boss_combat test_mechanics test_encounters test_guidance test_critical_parts test_aim_control test_report_damage test_required_elements test_rotation_search -q
python -m unittest test_core -q
node test_squad_checks.js
node test_history.js
```

The focused tests cover all five EX variants, real QTE hits and failures,
missile HP, cover exhaustion and piercing, part preservation, corrosion,
death stopping, reward selection, and shortened-clear rates. End-to-end
bounded searches completed for every boss using a fixed five-unit fixture.
Browser checks cover beginner guidance and the result evidence controls.
These checks establish software behavior; they do not establish game accuracy.
