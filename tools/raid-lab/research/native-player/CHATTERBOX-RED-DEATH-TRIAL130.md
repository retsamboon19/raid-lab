# Trial 130 Chatterbox red-death resource closure

Native trial 130 exited before combat. All archived errors in
`private/native-player-20261008a/probe-output-130/scene-verification.json`
contain two distinct original failed bundle keys:

| Bundle | Failed first chunk |
| --- | --- |
| `effect-spot-monster_library_assets_fx_m_red_lastdead_7cd9a96610fa8a2934332860c4f45b2c.bundle` | `6258b964ec36495e4bbc78377b4b6393` |
| `audiogroupspot_assets_lastdead_red_c10911b0ac48464a2ac33155bf081727.bundle` | `31b0071d82381681d3efd3ae492adc3a` |

The current installed Addressables catalog gives the exact key
`fx_m_red_lastdead` one quality-0 `UnityEngine.GameObject` entry, internal ID
`4c5649226b1e6f54caeba0c1bfcfe962`. Its original dependency key
`3182680209206631585` expands to those **two** patch bundles and eight
original built-in dependencies. The decoded effect bundle's `AssetBundle`
container maps the same internal ID to a `GameObject` named
`fx_m_red_lastdead`. This proves the audio bundle is in the original effect
resource dependency closure. It does not authorize restoring audio playback,
presentation services, or additional audio libraries; the current audio
output boundary remains unchanged.

`mechanics_observed_effect_closure.py` prepares a reusable exact observed
GameObject supplement from a native verification report, a current profile
closure, and an explicit catalog key. It fails if any observed failed bundle
is outside that key's Addressables closure, or if the decoded GameObject
does not match the catalog identity. Its stage command requires the exact
scratch receipt hash and writes only source-verified sparse chunks.

The source manifest is
`profile-assets/chatterbox-red-death-effect-source.json`, SHA-256
`1af639b66efd3da99b18c711b3f8592c82fa64823fdd83cbf5c03ce535705ac3`.
Its 2 patch bundles and 8 built-ins were staged to the private player while
idle. The stage added 40 verified chunks; the previous resource receipt
`79029cfcc8e82d594d53a73cb0c929e69b713bea3f69105a34155fc68a9f762d`
was backed up at `resource-chunks-before-79029cfcc8e8.json`. The new
resource receipt is
`4ac4b61208dab55c61692d36be3223117fdc12b0bbf40041bf252a5c53c9f164`.
The stage receipt `chatterbox-red-death-effect-staging-receipt.json` has
SHA-256 `a7926853ca45d30da19082d3dbda2201bb833dba1ed049e90f89fa49eb24aa4c`.
No installed game file changed, and this stage has not yet had a native rerun.

Commands from `I:/Nikke offline`:

```powershell
python tools/raid-lab/native-player/mechanics_observed_effect_closure.py special-chatterbox --catalog-key fx_m_red_lastdead --verification tools/raid-lab/private/native-player-20261008a/probe-output-130/scene-verification.json --base-closure tools/raid-lab/native-player/profile-assets/chatterbox-monster-mechanical-resource-closure.json --output tools/raid-lab/native-player/profile-assets/chatterbox-red-death-effect-source.json
python tools/raid-lab/native-player/mechanics_observed_effect_closure.py special-chatterbox --catalog-key fx_m_red_lastdead --verification tools/raid-lab/private/native-player-20261008a/probe-output-130/scene-verification.json --base-closure tools/raid-lab/native-player/profile-assets/chatterbox-monster-mechanical-resource-closure.json --output tools/raid-lab/native-player/profile-assets/chatterbox-red-death-effect-source.json --stage-receipt tools/raid-lab/private/native-player-20261008a/chatterbox-red-death-effect-staging-receipt.json --expected-before-receipt-sha256 79029cfcc8e82d594d53a73cb0c929e69b713bea3f69105a34155fc68a9f762d
python -m unittest tools/raid-lab/native-player/test_mechanics_observed_effect_closure.py -v
python -m py_compile tools/raid-lab/native-player/mechanics_observed_effect_closure.py tools/raid-lab/native-player/test_mechanics_observed_effect_closure.py
```

Two focused provenance tests and Python compilation passed. The next native
trial will distinguish whether the source-required red-death closure clears
management initialization or exposes a different unresolved mechanical
resource request.
