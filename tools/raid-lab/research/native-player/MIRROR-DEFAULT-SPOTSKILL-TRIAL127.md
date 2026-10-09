# Trial 127: original default SpotSkill fallback bundles

Trial 127 exited normally before combat. Its archived
`private/native-player-20261008a/probe-output-127/scene-verification.json`
contains four **distinct** failed bundle keys across all errors, even though
the first-failure field names only `Default_RLD_Energy`:

| Original catalog key suffix | Failed first-chunk hash |
| --- | --- |
| `Default_RLD_Energy` | `bd3d53c5cce41e88417dcde92978f336` |
| `Default_SR_Energy` | `a5419e1709d4f50ed68124b8903bf518` |
| `Default_AR_Energy` | `33b4af70404fe18f04442d7da1021f03` |
| `Default_RL_Energy` | `b63e6fa02cdb98a16896398acc50c025` |

These are source catalog assets of type
`NK.Spot.ScriptableData.Effect.MonsterSkillEffectData`. Current installed
`MonsterSkillEffectData.GetFullPath(string, AttackType)` RVA `0x061B4830`
forms the default skill path from a string name and nonzero attack-type suffix;
`MonsterEffector.<GetData>d__20.MoveNext` RVA `0x062E67D0` calls it and loads
the resulting Addressables location. This is a runtime string fallback,
separate from the MonsterTable numeric SkillId assets in the previous
`mirror-monster-mechanical-resource-closure.json`. The exact caller that
chooses the `RLD` name from Mirror's weapon rows is not established. It is
bound here by the original native request, not inferred from an `RL` row.

`mechanics_monster_resource_closure.py --observed-defaults` takes a current
profile, a native verification report and a new output path. It admits only
default SpotSkill bundle names that actually failed in that report, resolves
each to one exact installed catalog key and type, verifies original chunk
bytes and Addressables dependencies, decodes each scriptable asset, then
resolves its nonempty serialized AssetReference GUIDs where current catalog
keys exist. The four default scriptables contain five resolvable GUID assets
and twelve GUID references with **no installed catalog key**; those twelve
are recorded as unresolved rather than invented. The resulting supplemental
manifest contains nine verified patch bundles and two built-ins. It does not
claim a complete future runtime load closure.
For another profile, preparation requires its own current base monster
closure via `--base-closure-evidence`; the Mirror base is the default only for
this recorded trial. The guarded stage action remains Mirror-specific.

The immutable supplemental evidence is
`mirror-default-spotskill-source.json`, SHA-256
`8e8ab151f8390e7b765ec951014eb816e2248c8b8feb0966d016dbcfb3ac84b3`.
The guarded scratch staging added four new source-verified chunks, preserving
all previously staged bundles. The prior resource receipt
`0198cc98726b9b98a41df16c05937e8a8860e44875a503c6fdb60e0885286d74`
was backed up as `resource-chunks-before-0198cc98726b.json`; the new receipt
is `b0f6d40007c36875a5691976a3159c18033233bf1678fdbd9f2b11a301db6f43`.
`mirror-default-spotskill-staging-receipt.json` has SHA-256
`17b5ae00a4782d6a50b6a97c8033cbcbb3b0be331f904d757132239fd0f90b6c`.
No installed game file changed.

Exact commands from `I:/Nikke offline`:

```powershell
python tools/raid-lab/native-player/mechanics_monster_resource_closure.py anomaly-mirror-container --observed-defaults tools/raid-lab/private/native-player-20261008a/probe-output-127/scene-verification.json --output tools/raid-lab/native-player/mirror-default-spotskill-source.json
python tools/raid-lab/native-player/mechanics_monster_resource_closure.py anomaly-mirror-container --stage-observed-defaults --output tools/raid-lab/native-player/mirror-default-spotskill-source.json --expected-before-receipt-sha256 0198cc98726b9b98a41df16c05937e8a8860e44875a503c6fdb60e0885286d74
python -m py_compile tools/raid-lab/native-player/mechanics_monster_resource_closure.py tools/raid-lab/native-player/test_mechanics_default_spotskill.py
python -m unittest tools/raid-lab/native-player/test_mechanics_default_spotskill.py -v
```

Compilation and the one focused byte-integrity test passed immediately after
staging. A subsequent combined run of that test and the previous Mirror
closure tests could not open the scratch chunk store because a new native
player trial had locked it; the source registry test passed. Do not rerun
scratch-byte tests during an active player. The next native result must
distinguish whether these four defaults clear management initialization and
whether any of the twelve unresolved GUIDs are actually loaded.
