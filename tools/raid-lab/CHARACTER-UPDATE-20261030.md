# Current153 character update — October30–31,2026

## Complete visible-roster update — October 31, 2026

All three remaining characters are implemented in the active production Python
simulator: **Belorta: Pumpkin Witch (63/5184), Marian: Queen (19/5185), and
Rapunzel: Sanctuary (473/5187)**. Alongside Scarlet: Goddeath, Raid Lab now
matches **all206 visible installed153 resource IDs**. This supersedes the earlier
incomplete203-entry checkpoint below. The normal launcher reads the updated files.
No account, saved roster, installed offline client or historical native harness
was changed. No commit/push was performed for this task.

Each kit uses all ten original skill levels, verified weapons and existing stat
curves. The three additions match9,000 original base-stat values. All203 prior
raw/catalogue entries and all prior parsed skill entries remain unchanged;
Goddeath gains its source-backed Into the Fray qualification for Sanctuary.
The source-bound `current-roster.json` and `test_current_roster.py` compare the
entire visible-ID set on every future regression run.

Production mechanics include Belorta's immediate right-neighbor buffs and
direct-hit stealth removal; Marian's seven sequential spears, permanent wounds,
burst core strikes and separate own/off-burst buffs; and Rapunzel's full-charge
healing/extra damage, held shared shield, Into the Fray recipients, exclusive
mass revival, persistentDEF and40-second cooldown increase. Charge effects clean
up on release, reload, cover and death. Model revision:
`anomaly-source-runtime-v9-roster153`.

Verification on the frozen implementation:

| Command / check | Result |
|---|---|
| `python -m runner.complete_roster` |112 compiler-owned kits /745 effects |
| `python private/character-update-20261030/run_final_checks.py` |672 tests;0 failures/errors;4 pre-existing optional skips |
| `python -m runner.snapshot` |33/33 unchanged damage snapshots; no baselines regenerated |
| `python -m runner.doclint` |Passed206/206 catalogue/document consistency |
| `runtime/python.exe .../run_api_checks.py` |Real HTTP catalogue, imports, validation, five-team search and duplicate-job guards passed; synthetic history isolated |
| `python .../audit_belorta_witch.py` |892/892 source assertions |
| `python .../marian-queen/check_source.py` |270/270 source assertions |
| `python .../audit_rapunzel.py` |713/713 source assertions |
| Prior-data semantic preservation / `git diff --check` |Passed |

The full-suite wrapper excludes only standalone `test_api.py`, which requires a
live server and is executed separately against the real handler/worker with an
ephemeral loopback port. It writes synthetic reports only to a new private
evidence directory, never the user's report history. The bundled runtime was
used for the API test. The server and workers closed afterward.

The initial broad run exposed a fixed-slot boss targeting regression: AoE
eligibility had preceded the explicit formation-slot selector. Fixed-slot
precedence is restored and the original Harvester regression passes. Integration
review also reproduced Rapunzel's extra hit using a defeated historical target;
the exact153 NearAim/IncludeNoneTargetLast selector now reads the current live
aim policy. A real anomaly encounter regression proves identical positive
extra-hit traces with and without the stale target. Failed exploratory outputs
are preserved; the final gates are separate fresh receipts.

These are simulator/source checks, **not exact153 native full-fight parity**.
Marian's sequential flight/delivery timing (source20 interpreted as0.2seconds),
interval-transition phase and attack-counter gating/reset remain unverified;
her reports disclose this. Existing Goddeath contact geometry/counter boundaries
remain disclosed. No old152 receipt is reused as153 combat proof. RL animation
delays retain the established simulator model, without a new native timing trial.

Evidence and pre-import backups are under `private/character-update-20261030`,
including `before-missing-three`, `prior-data-preservation.json`, final unit/API/
snapshot/lint reports, three source audits and `missing-three-verification.json`.
The user requested normal PC shutdown after completion; it is the final action,
without forcing applications closed.

## Scope correction — full roster audit, October 31

The user challenged the assumption that Scarlet: Goddeath was the only new
character. A full comparison of the current installed CharacterTable against
Raid Lab finds **206 distinct visible resource IDs versus 203 implemented IDs**.
All simulator IDs still exist in the installed visible roster. Three additions
are still missing:

| Character | Resource ID | Name code | Weapon / element / burst |
|---|---:|---:|---|
| Belorta: Pumpkin Witch | 63 | 5184 | RL / Water / II |
| Marian: Queen | 19 | 5185 | MG / Fire / III |
| Rapunzel: Sanctuary | 473 | 5187 | RL / Fire / II |

Their names and IDs were verified using separate official English roledata and
the exact installed MPK rows. Evidence is
`private/character-update-20261030/roster-audit-20261031/missing-characters.json`.
This is installed-data visibility, not proof of current live recruitment windows.
The earlier September exclusion of hidden resource63 is stale: it is visible in
the current153 tables. Scarlet: Goddeath's implementation and tests remain valid,
but **the complete new-character update is not finished**. Implement the three
missing kits next; do not treat catalogue-only registration as combat support.
Future character updates must compare the full visible-ID set before choosing
the implementation scope, rather than selecting one current pickup.

Active work is in `I:/Raid Lab`, using the production Python simulator. The
installed offline client and the historical native battle harness are inputs to
research, not targets of this change. No account import, roster mutation, game
launch, publication, or native harness upgrade is needed for this addition.

Identity: Scarlet: Goddeath / 홍련 : 신살, resource 472, name code 5186,
CharacterTable 447201. Fire / Pilgrim / Attacker / AR / Burst III, 40 seconds.
Original Scarlet and Scarlet: Black Shadow remain separate identities.

Sources are the exact installed 153.6.10 / resource 657 / static 578481 MPK
archive and the official BlaBlaLink English/Korean character JSON. Immutable
snapshots and the bounded read-only table audit are under
`private/character-update-20261030`. The existing 152 native receipts are not
evidence of this character's execution on client 153.

## Work plan and source findings

1. Preserve all existing catalogue, raw, parsed and owned-account entries.
2. Add all ten source skill levels and the normal/changed weapon parameters.
3. Compile the three skills through existing production effects; test actual
   firing, Iai, normal-only crit, ammo refunds, own/off-burst and expiry paths.
4. Check catalogue/import/manual/search wiring, existing damage snapshots and
   document/data consistency. Keep results and unresolved boundaries here.

Confirmed source rules:

- Normal shot 1047201: 107.57% ATK, 90 RPM, 9 rounds, 1.17-second reload,
  200% core multiplier, native burst-energy 17000/34000, InstantBox piercing.
- Iai fires once per normal attack at the enemy nearest the aim. Its skill has
  zero base damage and delegates exactly one Damage function: 109% at level 10,
  changing to 218% during the own-burst enhancement marker.
- Permanent normal-only crit is 35% at level 10. Full Burst, including another
  character's cast, grants 60% general crit damage for ten seconds.
- Two normal critical hits refund one round only outside the own-burst marker.
  Own burst grants 50% normal-only crit and 116% attack damage for ten seconds.
- Changed shot 1047202 uses the CharacterSkill coefficient (115% at level 10)
  and 90 RPM override; its zero raw Damage/RateOfFire fields are placeholders.
  It has 999 rounds and lasts ten seconds. Width increases from 1000 to 2000;
  height remains 50. Burst also grants 120% ATK and one 3000% additional hit.

## Implemented and verified — October 31, Singapore time

Scarlet: Goddeath is available in the production catalogue, name/code imports,
manual simulation and search candidate evaluation. All ten levels of Skill 1,
Skill 2 and Burst compile from the canonical raw entry. The catalogue now has
203 real characters. Existing owned rosters are not automatically modified.

The addition reuses normal-only critical rate, conditional critical counters,
ammo restoration, effect-specific damage magnification and the temporary weapon
lifecycle. No shared damage formula or existing kit was changed. Canonical raw,
parsed metadata, parsed skills and directory entries for every earlier character
were compared against the original data and remain semantically identical.
The existing SSR Attacker AR base-stat curve matches all 3,000 source values
across the simulator's 1,000 supported levels; no stat-table change was needed.

The shared roster compiler includes the new kit, so regenerating parsed skills
does not erase it. The model revision is `anomaly-source-runtime-v8-goddeath`,
which prevents older reports being presented as results from this revision.
Reports containing this character expose the remaining hitbox/counter limits.
The boss implementation itself is unchanged.

Verification commands and outcomes:

| Working directory | Command | Result |
|---|---|---|
| Private character evidence | `python audit_target.py` | 354 original MPK/CDN identity, weapon and skill-value checks; no missing referenced functions |
| Engine | `python -m runner.complete_roster` | Compiled 109 compiler-owned kits / 708 effects; prior parsed entries unchanged |
| App | `python -m unittest test_goddeath -v` | 8 focused tests passed |
| App | `python -m unittest test_goddeath test_character_update test_complete_roster test_core test_source_provenance test_report_history test_burst_rotation -q` | 83 tests passed in 174.780s |
| Engine | `python -m runner.doclint` | Passed, 203/203 catalogue consistency |
| Engine | `python -m runner.snapshot` | All 33 existing damage snapshots passed; baselines not regenerated |
| Repository | `git diff --check` | Passed; only existing line-ending notices |
| Bundled runtime | Temporary loopback server using the real catalogue handler | 203 entries, exact 472/5186 identity and new model revision; server closed afterward |

The focused checks exercise actual firing and Iai hits, normal-only crit versus
skill crit, own/off-burst effects, two-critical-hit ammo recovery and its blocked
state, 999-round weapon mode and restoration, full-burst cycles, import investment
preservation, and equal manual/search results. Source comparison covers all ten
levels; runtime behavior tests use the production engine. These are simulator
checks, not full original-client combat parity.

An initial diagnostic print failed on the host's cp1252 console; subsequent
diagnostics use explicit UTF-8. The first focused run exposed two test-fixture
mistakes (missing caster in the Full Burst notification and assuming the first
ammo log was after firing); both were corrected without changing combat code.
The initial lint failure was the missing new name in the completion index; the
index now matches. No failed native trial occurred.

## Remaining validation boundaries

The original weapon's doubled InstantBox width is retained as source data, but
current153 collision axes, units and part/core contact enumeration are not yet
recovered. The simulator handles its selected target using existing pierce rules;
it does not invent extra part contacts or multiply damage by two for width.
Native critical-counter behavior while the burst marker is present is also not
established by table fields. The existing simulator counts critical events
continuously and gates the refund at activation. These limits appear on teams
containing Scarlet: Goddeath. A future exact153 native comparison must distinguish
these alternatives; old152 native receipts cannot certify them.

The saved scenario is
`../nikke-team-builder/docs/scenarios/홍련 _ 신살.md`. No historical native battle
harness, installed offline game, saved account, or prior regression baseline was
changed. The normal Raid Lab launcher reads these updated source files on its
next start. No persistent app server was running or restarted during the change.

## Source and backup locations

- [Official English role data](https://sg-tools-cdn.blablalink.com/vf-30/58bc3ce1526ab6d3ceee3c441b609ea4.json)
- [Official Korean role data](https://sg-tools-cdn.blablalink.com/hv-57/e89d9166d439d99d8ca750f2dee5827f.json)
- Installed decoded MPK archive: `I:/Nikke offline/transfer/update-20261030/current-tables.zip`
- Scoped audit and source hashes: `private/character-update-20261030/mpk-472-audit.json`
- Original source rows/semantics: `private/character-update-20261030/MPK-472-FINDINGS.md`
- Pre-edit catalogue/raw/metadata: `private/character-update-20261030/before`
- Other prior tracked source is preserved in the existing Git HEAD; no reset,
  staging, commit, push, account migration or cache restoration was performed.
