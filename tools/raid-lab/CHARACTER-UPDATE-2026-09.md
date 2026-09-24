# Coin Rush character update — 20 September 2026

Raid Lab now includes 202 visible characters, with executable Skill 1, Skill 2
and Burst definitions for Guilty: Mighty Bunny and Sin: Swift Bunny at all ten
skill levels. Both are Water / Missilis / Attacker / SR / Burst III / 40 seconds.
Their original Guilty and Sin versions remain separate units.

| Character | Resource ID | Account name code | Base table ID |
|---|---:|---:|---:|
| Guilty: Mighty Bunny | 404 | 5182 | 140401 |
| Sin: Swift Bunny | 405 | 5183 | 140501 |

The English catalogue and account-import mappings are updated together. Adding a
character manually retains modest editable defaults; importing a roster retains
its own skill levels and investment. Neither character is automatically added to
an existing owned roster.

## Necessary mechanics

- Both start in Stance. Holding a full charge for one second changes Bunny Mode
  and synchronizes allies already carrying a Bunny Mode. Ordinary allies do not
  acquire these states.
- Engage applies defence-ignoring damage to the specified attacks. Stance grants
  each character's own attack/charge or critical bonuses.
- Guilty's Mighty Stomp is one shot with a fixed 1.5-second charge; its charge
  bonus lasts that shot, while its attack-damage bonus lasts ten seconds.
- Sin's Swift Piercing lasts five seconds with a fixed 0.5-second charge. Its
  weapon and burst-gauge values differ from her normal rifle. Her ordinary
  full-charge bonuses do not apply during the transformed weapon window.

The Bunny mode selector appears when either new character is enabled in the
roster. Stance is the default. Engage schedules one opening hold, released at
2.2 seconds, on Guilty if present or Sin otherwise. One operator synchronizes
both; scheduling both to switch would toggle them back. The hold is an actual
firing delay in the model. The switching operator uses full-charge firing for
that run, even in assisted playstyle, so tap input cannot cancel the hold. Search
and manual simulations use the same input.
Opening cover or other interruptions can prevent the intended switch; this is
a control plan, not an unconditional starting-stat override. The search uses
the selected mode and does not automatically optimize mode switching mid-fight.

Reports include the selected mode and use model revision `coin-rush-roster-v1`.
Reports produced by earlier models remain historical results and are marked
stale until rerun.

## Sources and unchanged data

Canonical skill text and all ten level-value arrays were fetched from the public
BlaBlaLink CDN on 20 September 2026:

- [Guilty Korean skill data](https://sg-tools-cdn.blablalink.com/lo-00/d7c022b220dc31a94d63787600e71f5f.json)
  and [English identity](https://sg-tools-cdn.blablalink.com/bo-04/d6fef63aa4f620912a1bbadba5003b6e.json).
- [Sin Korean skill data](https://sg-tools-cdn.blablalink.com/na-19/e0c25204ae0243b5bb654cd88827e0e3.json)
  and [English identity](https://sg-tools-cdn.blablalink.com/ak-91/c221cac24a8278cee6975b70b9a80c96.json).

Skill definitions and selected state-transition primitives were adapted from
[MIT-licensed Jgaram/nikke-calc commit 1a873d5](https://github.com/Jgaram/nikke-calc/tree/1a873d52cabcdad0be0a539627613b2ccaa4bf28),
preserving Raid Lab's local engine extensions.

Values were cross-checked against installed client 152.8.11, static pack
`qa-260917-09c/563973`. Normal shots are `1040401` and `1040501`; burst replacements
are `1040402` and `1040502`. Sin's replacement uses a 999-round magazine, 300 RPM,
300% full-charge multiplier, and raw/target gauge values 14000/28000. Guilty's
replacement uses 250% full-charge and raw/target gauge values 28000/56000.

Comparing common IDs against the preserved 151 data found no numeric changes in
existing visible character skills, weapons or the 75,600 character-stat records.
Existing changes were catalogue order or visual effects. All 21 Favorite Items,
17 cubes, 255 cube-level records, equipment and option data were unchanged.
No new Favorite Item needs implementation. Hidden resource 63 is excluded.

Mast: Romantic Maid's Korean Skill 1 wording changed from `상태에 한하여` to
`상태일 때 한하여`. The values, state condition and installed skill functions are
unchanged; the canonical source wording is refreshed without changing her kit.

## Verification and limits

- All 530 catalogue compatibility simulations passed: skill levels 1 and 10 for
  every character, plus all Favorite Item phases. These check finite output and
  data compatibility, not every conditional activation.
- The 39 focused app checks passed, covering imports, mode-input consistency,
  original/alternate identity separation, roster coverage and existing combat
  behavior. Account investment and enabled state survive export/import.
- After the final input fixes, 55 app regressions passed, including burst
  rotations, report history, required elements and mode synchronization in
  automatic/assisted play with either Bunny alone or both squad orders.
- Six engine integration checks passed, covering synchronization scope, the
  double-toggle negative case, Mighty Stomp lockout, defence-ignore damage,
  fixed-charge timing and transformed-weapon exclusions.
- Engine document/data lint passed (202/202 kits), and all 33 damage snapshots
  passed without regenerating any baseline.
- History, squad-check and progress JavaScript checks passed. The running API and
  browser unit picker show both additions and all 202 supported characters.

The simulator still approximates aiming, boss geometry, projectile travel and
some encounter behavior. Passing these tests does not establish client-equivalent
damage or a guaranteed clear. The source data's presence does not assert that a
character's live recruitment window is open.
