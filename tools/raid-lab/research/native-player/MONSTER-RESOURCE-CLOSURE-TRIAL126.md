# Trial 126: Mirror monster resource graph

Trial 126 reached original management initialization after the trial-125
dynamic effect repair, then failed on the exact bundle
`scriptabledata_assets_scriptabledata/effect/monster/spoteffect/4510010123_225077f95edaa11700ef24d4dd8bacd9.bundle`.
Its first chunk is `8b0b22c1fa4178821db52a1407612d54`, 12,656 decoded
bytes and 2,068 compressed bytes. The native failure is in
`private/native-player-20261008a/probe-output-126/scene-events.jsonl`.

The installed catalog resolves the exact key
`ScriptableData/Effect/Monster/SpotEffect/4510010123` as
`NK.Spot.ScriptableData.Effect.MonsterIndividualEffectData`. The decoded
serialized record has two nonempty GUID references:
`PartsDestroyEffectReference` and `SkillCancelEffectReference`. Both are
exact current catalog keys with verified dependency bundles. The source
MonsterTable row for 4510010123 lists 30 skill IDs. Fifteen have exact
`ScriptableData/Effect/Monster/SpotSkill/<SkillId>` catalog assets of type
`MonsterSkillEffectData`; the other fifteen do not have that key and were
recorded absent. The fifteen decoded assets contain 64 nonempty serialized
AssetReference instances to 28 unique exact catalog GUID assets, including
projectile model/curve, hit, trail and other effect references. This graph
comes from current table IDs and serialized references, not bundle-name
matching or inferred skill timing. Each selected asset's installed
Addressables dependency closure was source-verified.

`mechanics_monster_resource_closure.py` is a reusable prepare-only generator
for current registered Intercept monsters. It accepts exact profile IDs,
checks current table rows and catalogs, and records absent SpotEffect or
SpotSkill keys instead of inventing an asset. The observed Mirror SpotEffect
key is required because native trial 126 loaded it. Among the other current
profiles, only Gravedigger has an exact SpotEffect key; Ultra and Chatterbox
do not. This catalog fact is not a claim that those bosses have no effects.

The immutable Mirror source manifest is
`mirror-monster-mechanical-resource-closure.json`, SHA-256
`df89d8debf03facb7a45b1de051709ac12a954dee6947c009f24285c861830ad`.
It covers 45 installed patch bundles and 10 original built-ins. The guarded
stage call added 213 source-verified chunks to the private sparse store,
bringing its receipt to 4,323 chunks. The current resource receipt SHA-256 is
`0198cc98726b9b98a41df16c05937e8a8860e44875a503c6fdb60e0885286d74`.
The stage receipt SHA-256 is
`47310afcc091d7aaeb0b729541c3d706b9a58fee8cd819145e7d54286dc41782`;
it points to the backed-up prior receipt
`resource-chunks-before-da0fdeb8e0b2.json`. Every included scratch
compressed chunk was compared byte-for-byte with the installed original.
No installed file changed.

Exact commands run from `I:/Nikke offline`:

```powershell
python tools/raid-lab/native-player/mechanics_monster_resource_closure.py anomaly-mirror-container --output tools/raid-lab/native-player/mirror-monster-mechanical-resource-closure.json
python tools/raid-lab/native-player/mechanics_monster_resource_closure.py anomaly-mirror-container --stage-mirror --expected-before-receipt-sha256 da0fdeb8e0b2c15255f8ddf13c653ab7d5993b582aee987492a5088db1c2e1b2
python -m py_compile tools/raid-lab/native-player/mechanics_monster_resource_closure.py tools/raid-lab/native-player/test_mechanics_monster_resource_closure.py
python -m unittest tools/raid-lab/native-player/test_mechanics_monster_resource_closure.py -v
```

The two focused tests pass: exact current catalog presence/absence for
registered profiles, plus closure and scratch-byte verification. A native
Mirror rerun remains necessary. The graph does not imply that all serialized
GUID assets are actively used in this fight, and it cannot preclude later
runtime string-addressed resources not exposed by these current tables or
serialized effect records. No source-linked boss timeline/director asset was
found in these `MonsterIndividualEffectData` and `MonsterSkillEffectData`
records; their Addressables dependency bundles are included, but no separate
director is invented. A later request should be added only from its exact
original load or a newly identified source reference.
