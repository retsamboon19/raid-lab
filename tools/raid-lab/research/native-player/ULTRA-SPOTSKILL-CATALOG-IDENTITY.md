# Ultra SpotSkill 510631 catalog identity

The first Ultra monster-closure preparation stopped because its previous
serializer required bundle `m_Name == "510631"`. The current installed
Addressables catalog has exactly one quality-0 key
`ScriptableData/Effect/Monster/SpotSkill/510631`, asset type
`NK.Spot.ScriptableData.Effect.MonsterSkillEffectData`, internal ID
`ff2ba7f6d5c459140acdccff89683348`, and bundle
`scriptabledata_assets_scriptabledata/effect/monster/spotskill/510631_b7a412903fd4e2bf46069251edecd81c.bundle`.
The decoded original bundle's `AssetBundle` container maps that **exact
internal ID** to its sole `MonoBehaviour`, whose MonoScript class is
`MonsterSkillEffectData` in `NK.Spot.ScriptableData.Effect`. Its serialized
`m_Name` is `510611`. Separately, the catalog key for 510611 has a different
internal ID, `fae15baef1ddd094a960d2a29cc0bc7d`, and a different bundle.
Thus 510631 is a valid catalog location with an internal serialized-name
alias, not a missing class or an ambiguous bundle.

`mechanics_monster_resource_closure.py` now selects the scriptable object
through the exact installed catalog `internalId` and bundle container key,
then checks its type and MonoScript class. It records both the requested key
name and the serialized `m_Name` plus `name_matches_key`. It rejects an
unknown internal ID; it does not choose an arbitrary same-class object by
name. Existing prior manifests were not rewritten.

New `profile-assets/ultra-monster-mechanical-resource-closure.json` SHA-256
`01dbc25da6530e86d612eb8a3a168545e2bc9e959170f7a90f3139a202d9de9c`
binds current Ultra's five present numeric SpotSkill assets, fourteen
catalog-resolved GUID assets, nineteen patch bundles and four built-ins.
One SpotEffect key and twenty-five numeric SpotSkill keys are recorded absent
from the installed catalog, without inferring substitutes. This is source
preparation only; it has not been staged or tested in native combat.

Commands from `I:/Nikke offline`:

```powershell
python tools/raid-lab/native-player/mechanics_monster_resource_closure.py anomaly-ultra --output tools/raid-lab/native-player/profile-assets/ultra-monster-mechanical-resource-closure.json
python -m unittest tools/raid-lab/native-player/test_mechanics_spotskill_catalog_identity.py -v
python -m py_compile tools/raid-lab/native-player/mechanics_monster_resource_closure.py tools/raid-lab/native-player/test_mechanics_spotskill_catalog_identity.py
```

The focused installed-container identity test passed (1/1), and Python
compilation passed. No scratch resources or installed client files changed.
