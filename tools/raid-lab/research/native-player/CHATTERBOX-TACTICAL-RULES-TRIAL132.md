# Chatterbox first attack: trial 132 tactical source audit

Scope: current installed Special Intercept Chatterbox, monster
`1520020113`, wave `6302004`, original-auto private trial 132. This is a
source/live-data feasibility audit for the **first** incoming hit, not a
validated boss-wide cover policy. No runtime, scratch or installed file was
changed.

The archived `private/native-player-20261008a/probe-output-132/scene-events.jsonl`
establishes this order:

| Line | Tick / native play time | Original observation |
| --- | --- | --- |
| 108 | 4 / 0.132 s | `MonsterCondition=FireCasting` (event 20029) |
| 111–112 | 87 / 2.871 s | `MonsterCondition=Fire`, then boss 8192 deals 604,650 to character 4098, actual damage 474,573, exactly its starting HP |
| 113–114 | 196 / 6.468 s | `MonsterCondition=Idle` |
| 115–116 | 197 / 6.501 s | first `MonsterAttack` event, node 7, target 4098, animation 3 |

There is no observed projectile-create/spawn or cover-damage event in that
first FireCasting-to-Idle interval. `MonsterAttackEvent` is therefore **too
late** to protect against this first hit. The boss's first attack targets
the third player slot (entity 4098) and kills it while its initial cover
starts at 520,100 HP. This trial does not exercise forced cover, so it cannot
prove the hit is unblockable.

The current installed catalog key
`ExternalBehavior/spot/bt_bbg002_intercept`, internal ID
`cbbb26f70f0938449b46f17eeee7644b`, resolves to
`externalbehavior_assets_all_7c875d479379cefc2e86fe0ab7c99590.bundle`.
Its decoded `ExternalBehaviorTree` JSON is parsed-equal to the retained
`private/offline-assets/trees/bt_bbg002_intercept.json`; the original
serialized JSON SHA-256 is
`b1f9f9590cca1f2e22e3a90b45fbe414fef69f374ec87accb330dcb332e797cb`.
The first selector branch is `IsTargetAlive(Player3)` node 5, then
`TimelineSkill` node 6 with `Shot_09` and casting action `JumpTo` node 160,
then `AttackV3` node 7 with `Shot_03`. This sequence and the live node-7
event strongly associate the early casting interval with `TimelineSkill`
`Shot_09`, but trial 132 did not log the active skill ID at tick 4/87; that
association is a source-backed inference, not a measured skill identity.

Current `MonsterSkillTable.mpk` SHA-256 is
`2333b5634cb6a855ecaf1be1f3e31a07683836e715b554430b50f3bcac15db9f`.
Its unique `Shot09` row is skill `510209`: `FireType=Instant`,
`IsUsingTimeline=true`, `Penetration=0`, `TargetCharacterRatio=100`,
`TargetCoverRatio=0`, `CastingTime=50` (raw table units), and
`CancelType=None`. The row makes character targeting expected, but its
zero cover-selection ratio does **not** establish that a raised cover
cannot intercept the shot. Original `MonsterAttackLogic.GetRatioTarget`
RVA `0x063BFF60` selects among skill target ratios;
`CreateTargetData` RVA `0x063BB280` uses a character position for target
type zero and cover position otherwise. The original timeline instant path
(`TimeLineInstant` `0x063C4300`, `FireInstant` `0x063BCEA0`) constructs a
ray and queries interactive collider layers before `FireHit`
(`0x063BC4D0`) applies damage to the hit entity. Thus target choice and
possible physical interception are separate original steps. This source
path is compatible with cover interception, but the exact tick-87 collider
and target type were not captured.

`TimelineSkill.OnStart` RVA `0x065485E0` selects the skill/targets and
starts the original timeline. `TimelineSkill.PlayEnd` RVA `0x06548DC0`
ends that action; the first observed Idle is at tick 196. A **diagnostic
candidate**, not yet a production rule, is to force the target's cover on
live first `FireCasting` only after confirming active node 6 / skill 510209,
and release on that action's original `PlayEnd` or its correlated Idle after
Fire/cancel. Do not key it to a future scripted tick or to node 7's later
`MonsterAttackEvent`. The corresponding release criterion must be observed
from the same action instance; a generic Idle from another action is not
sufficient.

## Trial 148: first-cast cover feasibility validated

The bounded private native trial at
`private/native-player-20261008a/probe-output-148` used the current installed
client and explicit diagnostic bare-character request SHA-256
`4e337cd2d0a9dedf3b5c882a5880e5ebe7d7ace59e56f08483dc2032a482590e`.
Its `chatterbox-cover-verification.json` passed with no errors; the original
battle completed 1,741 ticks, the private process exited cleanly, and the
trial recorded no native errors. The experiment used the original whole-squad
cover action while leaving original auto-aim and damage logic in place.

The original `TimelineSkill` node 6 selected skill `510209` and entered
`FireCasting` at tick 4. Cover engaged at tick 5. At the original `Fire`
event on tick 87, the boss's one positive hit was against target 4098's
cover entity `268587008`: original cover damage was 526,346, with 520,100
actual damage exhausting that cover. Character 4098 retained its full
474,573 HP through this first cast. The same node's original `PlayEnd` was
observed at tick 197; cover was released at tick 198. By tick 203, original
auto-fire had resumed for three squad members. These measurements establish
that this **first Shot09 cast can be intercepted by cover** in this
diagnostic build.

This is one first-episode result, not a Chatterbox-wide cover policy or a boss
win. The trial's terminal result still had zero surviving players and boss HP
143,990,610 of 160,011,052. Later casts, cancellation paths, other skills,
other roster builds, and repeatability have not been validated. The source
rule remains live first `FireCasting` after exact node 6 / skill 510209
identity, with release after that instance's original `PlayEnd`; a fixed
future tick or node 7 `MonsterAttack` is not an adequate trigger.
