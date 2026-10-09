# Current Intercept mechanical asset preparation

`mechanics_profile_assets.py` prepares a source-bound manifest for any of the ten
profiles in `mechanics-encounters-current.json`. It reads the installed client,
the current 2df7134a MPK archive, installed catalog and original chunk store.
It writes a new manifest under `profile-assets/`; it does not stage chunks,
change the installed game, launch a player or establish battle correctness.

The generator binds the exact Intercept row, WaveData row, PointData and
PointDataFly keys, wave paths, target Monster/MonsterModel rows, prefab and
SpotAI names. It resolves typed HD or SD Addressables entries for the
background and monster, the monster map, behavior tree, points, paths and
monster-linked QTE prefab candidates. Every selected dependency bundle is
checked against the installed catalog/index and either original built-in
entry or decoded chunk integrity. Ambiguous/missing keys, wrong types,
changed table rows, archive, client or unresolved bundles fail closed.
The current common mechanical geometry/presentation evidence remains linked
by SHA and bundle roles; the new profile background has its own role.

Prepared HD manifests:

| Profile | Exact current wave / monster / map | Manifest SHA-256 | Dependency closure |
| --- | --- | --- | --- |
| anomaly-ultra | 6302008 / 1520460146 / `sbg_desertbbg006_001` | `39049233dbf1bed5b98145c214791e59a59f1c3d7707a260233bec144723f77c` | 50 bundles: 35 verified patch, 15 built-in, 0 unavailable |
| special-chatterbox | 6302004 / 1520020113 / `sbg_cityforestunderbbg003_001` | `b91fcdccf7b7c229e091cadb6a4acea6810aca31b81d8ec042953cb5b106c63b` | 42 bundles: 28 verified patch, 14 built-in, 0 unavailable |

The Ultra source rows link four QTE entries (10152-10155, prefab
`QTEPrefab_Ultra`). No current QuickTimeEvent row links Chatterbox's target
monster. The manifest records that absence instead of inventing QTE assets.
These are **candidate** QTE resources; the active native behavior tree path
has not been tested for either encounter. Serialized `SpotSingleMap` geometry
is source geometry, not live camera/hitbox behavior.

Commands run from `I:/Nikke offline`:

```powershell
python -m py_compile tools/raid-lab/native-player/mechanics_profile_assets.py
python tools/raid-lab/native-player/mechanics_profile_assets.py anomaly-ultra --quality hd
python tools/raid-lab/native-player/mechanics_profile_assets.py special-chatterbox --quality hd
python -m unittest tools/raid-lab/native-player/test_mechanics_profile_assets.py -v
```

The two prepare calls succeeded with `ready_for_chunk_staging=true`. The
three focused tests passed. They bind all ten current profiles to exact MPK
rows, resolve typed Addressables roles in both HD and SD for all ten, and
reject a changed transport level or target mapping. Only Ultra and Chatterbox
have full decoded dependency manifests here; the other eight are registry and
catalog resolution checks, not staged or native validated fights. The next
step is a parent-owned staged chunk receipt and native encounter run after
the current private player exits.
