# Trial 136: early Unity main synchronization context

Trial 136 failed before table polling or any tactical control. The immutable
`private/native-player-20261008a/probe-output-136/scene-events.jsonl` records
`original_corlib_available` at 1791505212409, `il2cpp_ready` at 1791505212735,
then a `schedule_error` at 1791505214873: “couldn't find the synchronization
context of the main thread, perhaps this is early instrumentation?”
`mainWork.enteredAt` remained zero and `tablePollStage` was `not_polled` at the
unchanged 50-second probe deadline. The original `SplashSceneControl.Start`
gate fired later, at 1791505222222, and a deadline-time main-thread callback
did enter at 1791505262842. There is no basis to attribute this failure to
Ultra tables, assets, or the source-bound profile mapping: none had run yet.

The exact bundled bridge in trial 136 (`scene-probe.js`, SHA-256
`e5c5713811ebf8aaaa5ede999d2a7af8408318355bc58a05d19f2cbf5dc9fbe0`)
implements `Thread.schedule` by reading `this.synchronizationContext` *before*
calling its `Post`. Its getter checks the main thread's managed execution
context `_syncContext` (with a getter/static-data fallback) and raises that
exact error when none is installed. `il2cpp_get_corlib` becoming nonnull is
therefore an insufficient scheduling gate. Trials 133–135 reached the normal
Splash gate and then `main_work_delivery_ready`; 136 attempted the bridge
queue while Unity had not yet installed the context. Since the getter throws
before `Post`, the failed attempt did not enqueue a duplicate callback.

`headless_driver.js` now retains the single pending work block and retries
*only* that exact early-context error every 200 ms for at most 15 seconds from
the original queue time. Each attempt uses synchronous `Il2Cpp.perform(...,
'free')`; it never awaits the managed callback or keeps a worker attached.
Once Unity's real context is present, the unchanged bridge schedules the block
on the original main thread; subsequent work continues through the existing
source-checked `UniTask.Post(Update)` path. Other queue errors still fail
immediately. The existing 50-second probe deadline and private host limit are
unchanged. The edited driver SHA-256 is
`325df6f978dfb72a847421ae018a71ef0681a9cba4834f7029a7414eef6a2294`.

Validation so far: `node --check tools/raid-lab/native-player/headless_driver.js`
passed. No game or native run was made for this repair, and installed files,
scratch account state and host code are untouched. Parent's next fresh private
Ultra trial should distinguish this race from the previously observed resource
failure: if scheduling is delayed, expect one `main_context_pending`, followed
by `main_work_delivery_ready`, `headless_runtime` and
`original_tables_started`; later failures then belong to their actual native
stage. A non-context `schedule_error` or a context wait exceeding 15 seconds
remains a failure and must not be relabeled as resource progress.
