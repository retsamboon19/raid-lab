# Mirror trial 125: dynamic effect chunk repair

Trial 125 stopped during original `SpotManagement.OnInit`, before combat.
`probe-output-125/scene-events.jsonl` records an original chunk-load failure for
`effect-spot-monster_library_assets_fx_m_blue_lastdead_c61458257a4bf148468465f92b158bdf.bundle`.
Its first chunk is hash `43015207e502d1ba8b882ddd58ad6ff9`, original
length 99,403 bytes and compressed length 7,679 bytes.

The installed patch catalog/index maps that chunk to `store.cdb` offset
581,070,014. Installed compressed bytes begin with the zstd magic and hash to
`41d598973e16bf57f4092c55534f4ce15e1584fbeb91d35f4bba909dcc9a0550`.
The scratch store at that offset read as zeros before repair. The bundle was
absent from both `mirror-geometry-source.json`'s verified closure and the
scratch resource receipt, so this was a **missing dynamic load**, not source
corruption, a bad index, an overwrite of a received chunk, or encryption.
The installed Addressables catalog contains exactly one identity for this
bundle, but the Mirror monster prefab's static dependency set does not include
it. The current MonsterModel row has no effect asset field; a direct string
check of its decoded HD monster bundle did not contain `lastdead`. No other
distinct failing bundle request appears in trial 125's event log. That log is
not a complete forecast of all later dynamic loads.

The scoped `repair-observed-effect` command in `mechanics_encounter_assets.py`
verifies the installed DLL/catalog/index, original Mirror manifest and exact
first-chunk metadata; source-verifies the full bundle; checks the current
scratch receipt hash; and delegates only its verified chunks to the existing
sparse stage helper. Future fresh Mirror manifests include this observed
runtime bundle in the verified closure, and the ordinary Mirror stage path
rejects the old static-only manifest so the failure cannot silently recur.

Exact repair command from `I:/Nikke offline`:

```powershell
python tools/raid-lab/native-player/mechanics_encounter_assets.py repair-observed-effect --expected-before-receipt-sha256 83fb80b177ab2a2722dcdd46ca59d474a02fb3fdd08f2ceed249cb3b7d311479
python -m py_compile tools/raid-lab/native-player/mechanics_encounter_assets.py tools/raid-lab/native-player/test_mechanics_encounter_effect_repair.py
python -m unittest tools/raid-lab/native-player/test_mechanics_encounter_effect_repair.py -v
```

The repair staged 32 new original chunks, bringing the scratch receipt to
4,110 chunks. Every staged compressed byte was compared to the installed
source; the focused test also decompressed all 32 and checked the final
UnityFS SHA-256 `ee800e731461306dbefec160574f361dbad81288c195d82e72da797171670093`.
The source evidence SHA is
`56921c39ca86da7282625a15aa064917346e5224a5bdca7b25a1c262bb7015b0`.
The new resource receipt SHA is
`da0fdeb8e0b2c15255f8ddf13c653ab7d5993b582aee987492a5088db1c2e1b2`;
the prior receipt was backed up as `resource-chunks-before-83fb80b177ab.json`.
`private/native-player-20261008a/mirror-dynamic-effect-staging-receipt.json`
binds these values and the exact command. No installed files were changed.

The native rerun and any later dynamic resource requests remain parent-owned
and unverified. A later failure must be tied to its actual requested key;
unobserved effects should not be bulk-staged by name inference.
