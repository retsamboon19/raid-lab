# Trial 128 Mirror result contract

Installed client SHA-256:
`2df7134a6a9c3a8dbbde88402fc8d16d1d6c3f4c2d5e262bea78c3d78b96dd02`.
This audit reads the archived original trial and the installed-client inferred
native bodies. It does not rerun the player or alter result capture.

`private/native-player-20261008a/probe-output-128/scene-events.jsonl`
records `original_battle_result_observed` at line 414 and
`original_terminal_result` at line 416. The original `SpotFinish` result has
process state 8, `NK.BattleResult.Result=1`, native `get_SpotResult()=1`,
round `IsWin=true`, `Timeout=false`, `Retreat=false`, and play time
44.05580139160156 seconds after 1,339 tick calls. Its target HP is
5,565,245,380 of 5,800,000,000; `bossKilled=false`. The roster has five
characters, all five return false from the original `SpotEntity.IsAlive()`,
and `_deadCharacterList.Count` is four at the `SpotFinish` entry snapshot.
The last observed damage event in the trial log targets player entity 4100 at
tick 1338. The raw roster count is not a survivor count; the dead-list count
can lag the live-state check at terminal dispatch.

This is an **original Clear/Win result with a living boss and zero live
player characters**, not an apparent bridge bool inversion. The capture at
`mechanics_result_capture.js` hooks the installed `SpotManagement.SpotFinish`
RVA `0x0614BC60`, checks the object is `NK.BattleResult`, reads its raw enum
`Result.value__`, calls original `get_SpotResult()` (`0x06FCD8D0`), and reads
each roster character's original `IsAlive()` (`0x0638C660`). Its Boolean
conversion also reads `Timeout=false` and `Retreat=false` in this result.
The independent process state 8 corroborates Clear. No captured field claims
that the boss died.

The source path explains this apparently counterintuitive result:

- `InterceptProcess::.ctor` RVA `0x064DD080` clears inherited condition lists,
  puts `AllMonsterDead=1`, `TimeOut=0`, and `AllCharacterDead=2` into its
  **clear** list, and leaves its fail list empty. These enum identities are
  bound to installed metadata in `INTERCEPT-TERMINAL-TRIAL67.md`.
- `ProcessLogic.AllCharacterDead` RVA `0x063C9280` subscribes to
  `CharacterDead` event `0x2733`. Its callback RVA `0x063D35E0` checks a
  live-character selection for Count zero and constructs a
  `SpotFinishEvent(clearFlag, false, false, false)`.
- `ProcessLogic.<Finish>g__Action|4_0` RVA `0x063CA450` branches on the event
  `IsWin` byte: true calls `ProcessBase.Clear`; false calls `Fail`.
  `ProcessBase.Clear` RVA `0x064DE460` sets state 8. Its EndAction callback
  RVA `0x064FC970` explicitly constructs `NK.BattleResult` with enum argument
  **1** and dispatches original `SpotManagement.SpotFinish`.
- The `BattleResult` constructor RVA `0x06FCCE20` stores the enum at `+0x30`.
  `get_SpotResult` RVA `0x06FCD8D0` maps 1 to 1. In its single-round path,
  the constructor writes `SpotStatisticsData.IsWin` at `+0x10` as
  `Result == 1`. Thus `round.IsWin=true` is derived from the same native
  result enum; it is not a separate monster-defeat or survival verdict.

The all-character-dead clear condition is the **most likely** trigger for
trial 128, given zero original live characters and a live boss. The trial did
not capture which condition callback emitted the first `SpotFinishEvent`, so
`terminalCause="unknown"` remains the honest value. A timeout source is
unlikely at 44 seconds against the 180-second encounter limit, but the
`BattleResult.Timeout` flag alone is not a reliable source classifier in this
Intercept implementation.

Minimal next observation: passively count entry of the three original
condition callbacks (`AllCharacterDead` `0x063D35E0`, `AllMonsterDead`
`0x063D6310`, `TimeOut` `0x063D61C0`) and capture the **first**
`SpotFinishEvent` constructor `0x0642AC80` arguments/flags with current
tick and player `IsAlive` states. Correlate that source with the resulting
Clear/Fail transition and retain raw native result fields. If
`AllCharacterDead` fires first with zero live players, label terminal cause
`team_eliminated` while preserving native `Result=1`/`IsWin=true` and
`bossKilled=false`. Do not reinterpret Win as boss defeated or rewrite the
native result. Until that source event is observed, downstream comparisons
should display original Intercept Clear separately from boss kill and team
survival.
