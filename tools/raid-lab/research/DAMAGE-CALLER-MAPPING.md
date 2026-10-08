# Installed-client damage caller: bounded mapping

This note maps the current installed `GameAssembly.dll` SHA-256 `2df7134a6a9c3a8dbbde88402fc8d16d1d6c3f4c2d5e262bea78c3d78b96dd02`. It is a static reconstruction of `NK.Spot.Logic.Common.DamageLogic.GetDamage(CasterDamageData, TargetDamageData)` at RVA `0x063F3CE0`, not whole-fight parity evidence. Managed signatures come from `client-decompiled/metadata/installed-2df7134a/methods.jsonl` SHA-256 `eeae4be213f1604e7977a20bb4b3f9b96a6f419b3a0bcb7075b7d38e85614621`; class field offsets come from that install's `fields.jsonl`.

## Confirmed ordering and base

Publication checkpoint (October9): the `damage.py` hash discussed below is the
historical input to this mapping, not a receipt for the current source. Current
local CRLF `damage.py` SHA-256 is
`d2f3876d236a5a561d10fcb3931709d46c69188f0fce9c0ff0d43b3ed10ea80e`;
the published LF Git content SHA-256 is
`51a470180cec1bb119ed356c4a39f225e8c8e1dc36cd25d369335f4490bfe87f`.
Its final hit conversion now uses the recovered `DoubleToLong` behavior. The
remaining `_factor1..7` mapping limits still apply. Native whole-battle work is
tracked separately in [the native checkpoint](native-player/README.md).

The ordinary base branch (native `0x063F6696`–`0x063F67ED`; pseudocode lines 3562–3651) computes in `float32`, then widens to `double` for `CalculateDamage`:

```text
ignore = min(selected caster.ChangeDefIgnoreDamageRate.Ratio / 10000, 1)
         [lower bound not established]
target_defence_ratio = clamp(target.DefenceRatioRate / 10000, 0, 1)
effective_defence = max(single(target.Defence) * (1 - ignore), 0)
ratio_gate = max(1 - (1 - ignore) * target_defence_ratio, 0)
base = double(single((single(caster.Attack) - effective_defence)
                     * ratio_gate * statDamageRatio * damageRatio))
```

`damageRatio` is the `DamageRateInfo.DamageRatio` precursor `(StatValue(caster.DamageRatio) * an integer ratio / 10000 + StatValue(caster.DamageRatio) + integer component) / 10000` at lines 2050–2106; the exact producers of the two integer components are not yet resolved. `statDamageRatio` is `caster.StatDamageRatio / 10000` at line 2158 and is copied to `DamageRateInfo.StatDamageRatio`. The selected def-ignore term comes from the `Ratio` member of the attack-type-specific `ChangeDefIgnoreDamageRate` pair: copied caster-body offset 384, corresponding to managed offset 400. It must not be confused with the separate `DefIgnoreDamageRatio` field at managed offset 408. The normal branch's subtraction is **not** clamped to zero before the primitive. Another branch uses a positive `DefIgnoreValue` as the base directly; a positive def-ignore damage-rate branch uses `single(caster.Attack) * statDamageRatio * rate` (lines 3486–3545). Those branches must be modeled separately.

`CalculateDamage` at RVA `0x063F2140` receives the `double` base, `StatValue` shot count, integer muzzle count, and 22 single-precision rates. Its 25-argument signature is in `methods.jsonl`; the exact argument slots at `GetDamage` call RVA `0x063F6AF8` were checked against the PE x64 call setup, because Ghidra's C prototype drops stack arguments. The primitive applies shot/muzzle division, additive conditional/typed groups, and separate charge/element/resist products. Immediately on return, `GetDamage` calls `System.Math.Max(1.0, primitive)` at `0x063F6B31`; the PE literal at RVA `0x08627D50` is exactly binary64 `1.0`.

## Received damage, share damage, and final clamp

The target-side stage follows the primitive, not one of its 25 parameters (source lines 3875–3978; native `0x063F6C02`–`0x063F6EC2`). `GetElementReductionRate` RVA `0x063F7E70` returns a pair of `StatValue`s added to `TargetDamageData.DamageReductionRate` (offset 48) and `DamageReductionValue` (offset 56). The pair is **element reduction**, not a generic damage-reduction helper. For each negative combined integer, the code applies `(target.DamageReductionDebuffDecreaseRate + 10000) * combined / 10000` using signed integer division, before converting the rate to single precision and multiplying by approximately `0.0001f`.

When `TargetDamageData.IsShareInstant` (byte offset 84) is true, `shareIncreaseRate = -single(selected caster.ShareDamageIncrease.Ratio) * 0.0001f`; otherwise it is zero. The subsequent arithmetic is:

```text
clamped_primitive = max(1.0, CalculateDamage(...))
reduction = double(single(reductionRate + shareIncreaseRate))
            * clamped_primitive + double(reductionValue)
remaining = clamped_primitive - reduction
final_double = max(1.0, remaining)
```

`DamageRateInfo` retains `CalculateReductionShareIncreaseDamage = reduction`, `ShareDamageIncreaseRate`, `Damage0 = base`, `Damage1 = clamped_primitive`, `Damage2 = remaining`, and `Damage3 = final_double` (field offsets verified from metadata and output copies at source lines 4148–4171). The tuple's first item is `final_double`. The same `1.0` constant is passed into the second `Math.Max` at `0x063F6EBD`; there is no integer rounding at either clamp.

`GetDamage` wrappers returning `StatValue` (for example RVAs `0x063F31F0`, `0x063F35B0`, `0x063F39A0`) convert that double through `NK.Spot.Util.CommonUtil.DoubleToLong` RVA `0x06156DA0`. Its body calls `Math.Round(value, 5, MidpointRounding.ToEven)`, adds `+0.5` if the **original** input is positive and `-0.5` otherwise, then casts to signed `Int64` (truncation toward zero). Thus the ordinary positive path is nearest integer with half-up behavior after five-decimal stabilization, **not Python `round` ties-to-even**. The later HP application is outside this bounded mapping.

## Comparison to the current calculator

`I:/Raid Lab/tools/nikke-team-builder/calculator/damage.py` SHA-256 `31c3465c3953633aa8f14c2e2ad25eaa77e53b59324715858dec3db7e2b1b0fc` uses `_factor1..7`. `_factor2` has attack minus effective defence, but its clamp before other factors and its separate `atk_pct`, `enemy_def_down_pct`, and armour-break conventions are not the native caller's field/order mapping. `_factor3` resembles the native additive critical/core/category/burst/range group; `_factor4` resembles the separate charge product; `_factor5` resembles the second additive typed group; `_factor7` resembles the separate element product. This is structural correspondence only, not proof that the calculator's percentages and branch predicates equal native values.

The important mismatch is `_factor6`: it multiplies by `1 + received_dmg + conditional split_dmg` before its final `max(round(damage), 1)`. Native applies signed target reduction **after** the first `max(1, primitive)`, includes a flat reduction value and element-reduction tuple, conditionally subtracts `caster.ShareDamageIncrease` from the reduction rate, then clamps to 1 again. Mapping UI `received_dmg` to a negative `DamageReductionRate` can reproduce only the simple rate-only subcase; mapping `split_dmg_pct` to native `ShareDamageIncrease` requires verifying the buff-to-field producer. The current calculator's `round` and clamp order also differ from `DoubleToLong`.

## Explicit limits

This pass did not resolve every producer of the 25 rate arguments, the two `DamageRatio` integer components, the exact lower bound of def-ignore, the source of `DefIgnoreValue`, the mapping from parsed Raid Lab buff names to native `TargetDamageData`/`CasterDamageData` fields, or later HP/parts/share routing. Do not describe the current `_factor1..7` implementation as native equivalent on these grounds. The source and PE disassembly prove caller ordering, clamps, target reduction/share arithmetic, and wrapper rounding for the mapped paths only.

Evidence: `I:/Nikke offline/client-decompiled/pseudocode/installed-2df7134a/0x063F3CE0.c` SHA-256 `ed886a6798221330fa7810d4890560b015530f6f821766ba0097e04d2be7a987`; `0x06156DA0.c` SHA-256 `19e2f28db1edd122b154a5a1de512ed04c93c1d150aed0e54a08a063049d4812`. Relevant PE disassembly was read directly from the exact installed DLL; no game, account, or hook was changed.
