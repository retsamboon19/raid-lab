# Native mechanics research source snapshot

This directory preserves the authored, results-only original-engine battle harness and tactical controller source used for the Raid Lab investigation. It is **research source**, not a packaged native backend or a replacement for Raid Lab's production Python simulator. `source-index.json` gives the original workspace-relative path, SHA-256, and byte count for every copied source file. Code files are copied byte-for-byte.

The current installed-client binding is `GameAssembly.dll` SHA-256 `2df7134a6a9c3a8dbbde88402fc8d16d1d6c3f4c2d5e262bea78c3d78b96dd02`. Private native trial 123 completed the original Kraken battle and passed both observed tactical checks: the seven active Break QTE targets were hit without observed Counter hits, and original squad cover protected the five-character team through the tested node 230 missile/follow-up sequence before firing resumed. Its native result matched trial 120. These checks cover one diagnostic fixture and sequence; full accuracy, equipped user builds, other Kraken attacks, and all-boss tactical coverage remain unverified. The Mirror Container source and mechanically required chunk closure have been staged in the original private workspace, but **no Mirror native fight has run**. The 21 fixed boss entries in `evidence/BOSS-AUTOPLAY-COVERAGE.json` are an inventory, not 21 validated fights. See `SMART-AUTOPLAY-IMPLEMENTATION.md` and `evidence/BOSS-TACTICAL-SOURCE-RULES.json` for the bounded policies and current source mappings.

`modules/` contains the headless driver, original-mechanics adapters, observers, and tactical policies; `runner/` has staging, request/encounter validation, and trial verification code; `host/` retains the private desktop and deny-all network guard source; `tests/` has focused contract checks; `fixtures/` contains explicit diagnostic synthetic/bare requests and the current encounter registry. These are source files only. The private trial logs, game executable and DLLs, decoded bundles/chunks, raw decompiler output, account data, and large serialized geometry manifests are intentionally absent. External evidence paths and hashes are listed in `source-index.json` without copying the files.

The snapshot is not standalone. Original workspace paths in the code refer to the installed client, current MPK archive, metadata, original signed catalog and patch store, private Unity player, compiled host/Frida binaries, and private staging receipts. Preparing or running it requires that separate bounded Windows research workspace, its dependencies (including UnityPy/zstandard and the existing bundle parser), and a fresh source/hash review. Do not interpret a successful source-level test or native diagnostic as production integration. Raid Lab's production recommendation/search path still uses its Python engine.

Verify the published source bytes and explicit file set from the Raid Lab repository root:

```powershell
python tools/raid-lab/research/native-player/verify_snapshot.py
python tools/raid-lab/research/native-player/verify_snapshot.py --tests
```

The optional second command reconstructs the original sibling layout in a temporary directory and runs four Python mock input/receipt suites plus three Node QTE, cover, and threat contracts. It never invokes the original DLL, resource loader, native player, or private trial. The local `.gitattributes` keeps Git from rewriting the copied files' bytes, so their published SHA-256 values remain meaningful.
