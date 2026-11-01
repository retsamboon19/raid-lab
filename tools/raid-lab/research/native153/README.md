# Original153 native-engine research source

Source-only checkpoint, November 1, 2026, after successful direct-broker and HTTP jobs, five fixed-input native observations, and one actual Kraken mock battle. This is a review snapshot of the authored implementation, not a runnable client distribution or a general native simulator release. The existing `research/native-player` snapshot is untouched.

The fixed practice pipeline invokes the original installed153 combat engine inside a bounded, isolated Unity host. Python prepares, orchestrates and verifies the run; combat results come from the native engine. This snapshot includes snapshot reconstruction, original team/transporter preparation, scene and loading-overlay bootstrap, native locale initialization, scheduling, full shared-RNG verification, original pre-cleanup packet export, independent managed protobuf decoding, runner locking, and the fixed-fixture app/broker integration.

## Observed results

All three native runs completed the original 90-second fixed practice battle, passed both full shared-RNG OnStart boundary checks, captured the original protobuf result, and passed independent decoding and the frozen-input, preference and resource guards. The matching references were three real installed offline practice runs with the same ordered team and full-auto controls.

| Reference | Native candidate | Reference score | Native score | Difference |
| --- | --- | ---: | ---: | ---: |
| 1 | 20 | 1,013,203,602 | 1,010,931,464 | -0.224% |
| 2 | 21 | 1,031,870,235 | 1,030,291,390 | -0.153% |
| 3 | 22 | 1,034,199,644 | 991,714,359 | -4.108% |

These are three paired observations, not a statistical confidence interval or proof of exact combat parity. Combined damage differs by -1.505%; the third pair differs more than the first two. The requested criterion is dependable comparison within ordinary variation, rather than identical numbers. These samples are encouraging but insufficient to establish accuracy across teams and encounters. Full parity is **unverified**. Coverage is limited to the captured Anis: Star / Trina / Drake / Alice / Scarlet team and one 90-second range setup. Other teams and edited builds are unsupported by the current fixed-fixture adapter and must fail explicitly.

The fixed-reference1 release is now enabled locally. A fresh direct-broker job completed with score **1,007,303,396**; a separate fresh HTTP job completed with score **1,010,931,464**. Both passed the original 90-second battle, full shared-RNG, original-packet and independent-decode gates. The app's native adapter tests passed (21 checks), as did the page lifecycle tests (13 checks). These are distinct runs, not replayed response files.

Across five native executions of those same fixed inputs, four returned **1,010,931,464** and one returned **1,007,303,396**: approximately 0.36% spread. The three actual practice runs used different captured seeds and varied by approximately 2.07%, so those spreads describe different experiments and are not a formal equivalence test.

One actual current153 Kraken mock battle reached phase 5 with **1,632,818,679 damage**, ending at displayed **1:28** with all five characters defeated. Its existing preset and builds were captured without manual target/cover actions. A matched current153 native Kraken battle has **not** run. Separate Kraken helpers are preserved as incomplete preparation: the mode gate still rejects the captured mock-battle flag, and the tactical port has unresolved binding/field dependencies. Neither is enabled in the app. Historical152 Kraken targeting evidence cannot validate this current153 capture. A future baseline must use matching controls; smart targeting and cover must be evaluated separately when enabled.

The fixed-fixture page and recovery/cancellation lifecycle are implemented, but actual browser rendering and user interaction remain **unverified**: the computer-use tool could not establish the Opera URL under its URL policy. The existing default calculator engine remains separate; this snapshot does not make arbitrary teams/builds native-supported. There is no Python combat fallback in the native job path.

## Layout and dependencies

`offline/` mirrors selected source paths from the offline research workspace; `app/` mirrors the small active-app native adapter and its tests. `SOURCE-ALLOWLIST.txt` enumerates every copied source file. `SOURCE-INDEX.json` records its origin-relative path, exact SHA-256 and size. The copied web page/script and API adapter tests cover the explicit fixed-fixture interface; the already tracked app server supplies its routes. No recursive directory copy was used.

The copied source is unchanged. Paths and immutable digest constants deliberately retain their original review context. The snapshot's nested layout is for inspection; it is not a relocated working installation. Source files refer to excluded private bindings, proofs, captured inputs, owned client files and asset fixtures. Their absence causes the guarded pipelines to stop. Tests requiring those private dependencies cannot run from this snapshot alone. Mock tests and orchestration tests are retained as authored source, not represented as a standalone passing public test suite.

The C# decoder requires separately built generated protobuf types and Google.Protobuf. Neither those assemblies nor generated game protocol sources are included. No DLL, executable, metadata export, decompiled body, catalog, resource, capture, raw log, replay input, account data, result packet, or private release is included. Signature guards and public asset/type identifiers inside authored code remain part of the implementation; their supporting native evidence is excluded.

The host retains explicit output/UI and audio boundaries. Restoring the original loading/intro, locale and selected scene services established the observed startup state; it does not certify every omitted scene/UI effect or arbitrary gameplay. No license for the original client or assets is granted here.
