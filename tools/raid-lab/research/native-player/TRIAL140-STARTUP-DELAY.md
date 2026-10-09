# Trial 140: startup delay before the Chatterbox diagnostic

Scope: bounded read-only comparison of archived private trials 137, 139 and 140.
No native player was run and no staged or installed file was changed. Trial 137
and 140 use the same `special-chatterbox` request (wave 6302004) and identical
`mechanics-request.json` SHA-256
`be170ec1716b29033655dfa3f105cd36ed0041b011a4de21e57a0df380822024`.
Their `resource-chunks.json` SHA-256 is also identical:
`9c801428833df2ed0e92a5a9df936d8102c9794b4526c2f3ac36295bd6a6e77c`.
Trial 139 is the `anomaly-ultra` baseline. Probe scripts differ, so this does
not prove byte-identical overall trial inputs.

Elapsed milliseconds from each trial's `gadget_loaded` row in
`private/native-player-20261008a/probe-output-<n>/scene-events.jsonl`:

| Original startup phase | 137 Chatterbox | 139 Ultra | 140 Chatterbox |
| --- | ---: | ---: | ---: |
| IL2CPP corlib available | 759 | 760 | 654 |
| original Splash `Start` parked / main delivery ready | 5,892 | 5,005 | 18,680 |
| original tables start → loaded | 6,497 → 11,072 | 5,743 → 11,245 | 19,312 → 24,200 |
| original `SpotSetting.Load` catalog start → ready | 11,191 → 12,706 | 11,366 → 12,242 | 24,868 → 45,230 |
| original aim/prefab prerequisites ready | 14,923 | 16,208 | 55,850 |
| original `SpotManagement.OnInit` returned | 15,001 | 16,998 | 56,473 |

The table load itself took 4.89 seconds in 140, within the 4.58–5.50 second
comparison range. Three *other* delays consumed the startup budget:

- Original Splash `Start` was parked 13.7 seconds later than 137. At elapsed
  7.749 seconds, `main_work_stalled` recorded work queued at absolute
  `1791506014219`, `enteredAt: 0`, with no table poll yet. The Unity main work
  delivery was not ready until elapsed 18.686 seconds. Corlib readiness was
  normal at 0.654 seconds, so the delay is after IL2CPP availability and
  before the bounded main-thread delivery point.
- `SpotSetting.Load` took 20.362 seconds in 140 versus 1.515 and 0.876 seconds.
  The 140 dependency snapshot at elapsed 45.206 seconds showed an Addressables
  `InitializationOperation` with `m_loadCatalogOp` valid and its chained
  CatalogDatabase operation `status: None`. The operation became ready 24 ms
  later. The snapshot establishes a pending catalog dependency, not whether
  disk, cache, provider scheduling or main-thread contention caused the wait.
- The mechanical prefab phase took about 9.11 seconds in 140 versus 1.86 and
  3.57 seconds. `UIAimControll` alone took 4.991 seconds in 140 versus 0.287
  and 0.080 seconds. This happened after the catalog delay, with the same
  Chatterbox resource-chunk receipt as 137; it is another wait, not evidence
  that a new mechanical asset was missing.

At absolute `1791506062709` (elapsed 50.673 seconds) the existing probe
deadline recorded `completed:false`, `pendingMain:true`, and a just-queued
main command (`queuedAt:1791506062699`, `enteredAt:0`). Original `OnInit`
returned only at absolute `1791506068509`, after that deadline. The private
host then reached its 60-second timeout (`native-player-run.json` return code
124; `scene-verification.json` has `complete_battle_executed:false` and
`clean_quit_observed:false`). There is no `original_chatterbox_cover_probe_ready`,
node-6 observation or combat tick in 140. Its timeout does **not** test the
repaired skill observer or the first-cover policy. Trial 137 did reach tick 4
with clean exit, though its older observer failed there. Trial 139 completed
its different encounter with clean exit.

Mirror 141 completed under the same 50-second probe deadline with the same
`resource-chunks.json` SHA-256. Its phases were normal: Splash parked at 4.068
seconds, tables loaded at 9.291 seconds, `SpotSetting.Load` ran from 9.397 to
10.229 seconds (0.832 seconds), and original `OnInit` returned at 12.173
seconds. It recorded neither `main_work_stalled` nor
`mechanics_catalog_dependency`; `scene-verification.json` says the original
battle completed. Thus 140 was **not a persistent global slowdown** across
the adjacent private runs. The Chatterbox-specific hypothesis is also weak:
137 used the same Chatterbox request and chunk receipt and initialized in
15.001 seconds. In `headless_driver.js`, the slow `Addressables.InitializeAsync`
catalog phase precedes `runMechanicsLifecycleProbe`, which is where the
encounter-specific work begins. These observations support a transient
startup/main-delivery or shared Addressables scheduling problem, but do not
identify its system-level cause.

The previous one-time `main_work_stalled` latch hid later queue stalls after
140's early pre-Splash event. Also, the catalog dependency snapshot was emitted
only when the main-thread poll eventually ran 20.338 seconds after catalog
start; it did not prove that the Addressables operation itself consumed all
of that interval. To make the *next* Chatterbox trial discriminating without
extending either deadline, `headless_driver.js` now logs a stall once per
queued main command and emits one `mechanics_catalog_poll_gap` record if
polling pauses for over 3 seconds. That record includes elapsed catalog time,
the poll gap, and the current main-queue wait. A long queue wait identifies
main delivery latency; a long poll gap with short queue wait identifies
timer/worker scheduling latency; regular polling plus a pending dependency
points to Addressables/provider work. The change is observation-only and
`node --check tools/raid-lab/native-player/headless_driver.js` passed. It has
not been native-tested. Do not raise the deadline or repeat the unchanged
trial 140 probe.

Evidence read: archived `scene-events.jsonl`, `scene-verification.json`,
`native-player-run.json`, request JSON and resource-chunk receipts for 137,
139, 140 and 141; current `headless_driver.js` startup sequence. SHA-256 values
above were calculated from archived bytes; no
historical receipt was rewritten.

## Trial 142: the delayed catalog poll was waiting for main-thread file I/O

Trial 142 used the new bounded phase observer and again returned from original
`OnInit` before the outer deadline, at elapsed 36.087 seconds. It did not
reach the Chatterbox diagnostic because the remaining battle work exceeded
the unchanged deadline. The catalog began at elapsed 14.391 seconds; the
first subsequent main poll ran at elapsed 31.403 seconds. Its
`mechanics_catalog_poll_gap` recorded `pollGapMs:17011` and
`mainQueueWaitMs:16947`. Thus nearly the entire gap was the queued main
command waiting to enter, **not** the Frida poll timer sleeping or 17 seconds
of observed `get_IsDone` polling. The per-command watchdog recorded a second
`main_work_stalled` at elapsed 19.799 seconds. Catalog readiness followed the
delayed poll at elapsed 31.471 seconds.

The watchdog sampled the Unity main thread during that wait. Its PC was in
an external system module (`0x7ffaf0760e84`), so the PC alone does not name
the operation. The retained GameAssembly frames, mapped to the exact installed
`2df7134a…` method index and recovered bodies, form a much narrower call chain:

| Sampled return RVA | Recovered method start | Call-path evidence |
| --- | --- | --- |
| `0x03F9AB52` | `System.IO.MonoIO.Read` `0x03F9AA90` | native file read boundary |
| `0x03F9567A`, `0x03F9547F`, `0x03F957E3` | `FileStream.ReadSegment` `0x03F95610`, `ReadData` `0x03F95400`, `Read` `0x03F956C0` | synchronous stream read |
| `0x03F811CD` | `Stream.Read` `0x03F810E0` | stream wrapper |
| `0x07773DE5` | `GenericHashUtility.ComputeFileHash` `0x07773B20` | reads file to compute hash |
| `0x07776D17` | `SignUtility.VerifySignature` `0x07776A60` | verifies signed file |

`VerifySignature` opens its supplied signature file, then calls
`ComputeFileHash` on the content path. `ComputeFileHash` calls
`File.OpenRead` and reads through the stream. The stack therefore supports
that the main thread was **inside original signed-file verification and a
synchronous file read** while the probe's catalog poll waited. The sampled
RVA sequence does not reveal the file path, the storage layer beneath the
external PC, or why that read took so long; it does not justify bypassing
signature checks or increasing timeouts. Frames below `0x008A1000` and the
last two fuzzy frames were not assigned a reliable managed caller.

The next discriminating bounded check before another Chatterbox claim is to
capture the original `VerifySignature` content/signature path arguments and
file size at entry, then pair them with one exit duration and the existing
per-command queue timing. This identifies whether a specific staged signed
catalog file is slow or whether the wait is transient disk/host scheduling.
It should remain read-only in the private child, preserve the exact original
verification call, and stop at the current deadline. A successful native run
after the read returns is still needed before the Chatterbox skill/cover
diagnostic has been tested. No further native run or code change was made for
this source mapping.

## Trial 144: original signed catalog verification observed

The bounded observer preserves original VerifySignature and logs only supplied
file paths, duration and boolean result. The original core/catalog.ndb check
took3967ms and returnedtrue; core/raw/5256e42159f92f5671525298beb80762.db
took96ms and returnedtrue. Catalog poll gap7342ms/main queue wait7261ms
includes that measured3967ms verification, but does not explain every queued
millisecond or prove the cause of142's longer stall. No signature bypass,
cache substitution or timeout increase. Trial144 passed startup and reached
native tick4, then stopped on the distinct Chatterbox observer error
`Original node 6 monster absent`; clean exit34.673s. It does not establish
cover success or a complete battle. Correct original SharedBattleMonster.Value
then BattleMonster.Monster lookup is now implemented and mock-tested; the next
check concerns this native readback, not more startup scanning.
