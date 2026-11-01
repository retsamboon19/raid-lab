# Source-only selection and privacy review

Included: 129 explicitly selected authored source files (JS, Python, C#, csproj, HTML and Markdown), including focused tests, current bounded orchestration, and incomplete Kraken preparation with its handoff. Source copies were verified byte-for-byte against the source index. The old research snapshot is unchanged.

Excluded: all capture collectors and their captured data; replay input/expected-state files; account and inventory payloads; result packets; raw logs; JSON source proofs and receipts; metadata exports; decompiler/disassembly output; catalogs; resource stores; native binaries; generated/build outputs; private native releases. Only the newly authored source index is JSON. Historical duplicate candidate sources and unrelated old native arithmetic/service wrappers were omitted. The long BATTLE-ENGINE worklog was not copied because it mixes account/setup history and private evidence chronology; README supplies a bounded public status summary.

Implementation scripts that extract or validate inputs are included as code only. They contain field names and private-relative paths/digest references, not the input payloads. Fixed native type/RVA guards and asset identities inside authored implementation code are retained. Source references do not make the excluded dependencies available.

Review performed: explicit filename/type allowlist; no symlink/directory copying; exact post-copy SHA checks; content scan for the known account identifier, private-key blocks, nonempty password/access-token assignments and literal inventory serial payloads. No matches were found. This is a bounded engineering privacy check, not an assertion that a generic secret scanner proves absence of every possible sensitive string. No captured build/stat arrays or RNG-state fixtures were copied.

The root task prepares the source-only commit on existing main. Unrelated roster work remains outside this commit. Source tests were not rerun merely to create this snapshot, and no native process was launched by publication. Kraken preparation is explicitly incomplete and has no current153 native outcome proof. Capture inputs, current native binding JSON and disassembled method bodies remain excluded.

Git attributes preserve this snapshot's exact line endings and existing trailing blank lines, so checkout bytes continue to match its source index. Runtime source files were not reformatted to satisfy publication whitespace checks.
