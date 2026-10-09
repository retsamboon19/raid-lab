# Ultra first break episode: native observation and source scope

This is a source and observation rule for the first `anomaly-ultra` episode,
not a tested tactical input. Trial 139's immutable
`private/native-player-20261008a/probe-output-139/scene-events.jsonl` has
SHA-256 `874880c520415f6b5c39dc2f57c0d2b1e93f0e3aa249de7cfd480459f7dc9cae`.
The fight completed under original auto input. No
`MonsterBreakColliderHurt` or `MonsterSkillInterruptionEvent` was observed;
all 11 `MonsterAllBreakCollider` events reported `isBreak=false`.

For the first activation, owner 8192/table `1520460146` emitted
`MonsterBreakColliderActiveStart` sequence 2 and `ActiveStarted` sequence 3
at tick 320, native playtime 10.560, with `CastingTime` 6.300 and
`EndAtRemainCount` 0. The live snapshot at tick 321 had `playing=true`,
`nativeIsAllBreak=false`, and exactly three enabled Unity-live type `Break`
colliders, each with original HP/maxHP `280000`:

| Collider ID | Original name | Native world bounds center (x, y, z) |
| --- | --- | --- |
| 819204 | `break_col_04` | (-13.2860546112, 19.9987392426, 67.1094436646) |
| 819205 | `break_col_05` | (-24.4302692413, 26.5920867920, 68.2645797730) |
| 819206 | `break_col_06` | (-8.8061676025, 28.1959762573, 63.5406951904) |

Each reports `liveBreakTarget=true` and aim-point basis
`UnityEngine.Collider.bounds.center`. No `Counter` or `Choice` collider was in
this *first* sampled episode. A bounded candidate rule may select one of
these three only while the same original activation sequence is current,
the live collider remains enabled and positive-HP type `Break`, and the
original target/position can be reacquired. Never apply this first-episode
observation to later Ultra episodes or infer that a chosen shot will damage it.

The current-client source inventory in `BOSS-TACTICAL-SOURCE-RULES.json`
(SHA-256 `75e8114fdcfc4f72b25c2f44a3a44c19a1c35513bce338eaafe1e95f78f8a270`)
maps Ultra's `MonsterSkill` row 510636 to `Shot03`, `BreakCol`, and
`break_col_04/05/06`; row 510637 maps `Shot04` to `break_col_01/02/03`.
The retained original tree `bt_bbg006_InterceptAnomalous.json` (SHA-256
`0befa8c9d8ec021b89d77540c68d6213c4144c97a8b5c1150d38bcd547b28063`)
has node 33 `AttackV3 Shot_11` followed in its sequence by node 35
`TimelineSkill Shot_03`. Trial 139's prior `MonsterAttack` at tick 285 names
node 33/animation 11; it does **not** identify the later activation's skill
ID. Row 510636 is the exact source candidate for the observed collider-name
family, not a proven event association. Break cancellation, target HP loss,
weapon eligibility and required damage per part remain unverified until a
source-bound original-input trial records positive `Hurt`, HP decrement and
native completion/interruption in this same activation episode. The inactive
snapshot at tick 546 had no colliders; `isBreak=false` at ticks 544/545.
