# Current153 Kraken input and process helpers — prepared only

These new helpers are not integrated or native-tested. No current practice,
stager, broker, release, shared ledger or installed files were changed.

`prepareCapturedKrakenFixture153(runtime, staticImage, pin, emit, input, expected,
bindings)` requires `input = {fixtureInput, snapshotInput, krakenCapture}`.
The fixture/snapshot/expected formats are the existing original capture
extractors' formats, supplied from a future actual offline Kraken capture.
They must preserve the actual Kraken capture's five actors in order; no practice
team IDs are hardcoded. Practice-derived packets and
cross-capture/run data reject before original construction. All61 transporter
fields and the376-byte current layout are required.

`krakenCapture` is a separately frozen provenance receipt descriptor:

```javascript
{
  kind: 'actual_offline_kraken_prebattle',
  clientSha256, captureSha256, receiptSha256,
  fixtureInputSha256, snapshotInputSha256,
  orderedCharacters: [{slot, tableId, nameCode} /* five captured records */]
}
```

The later stager must verify those actual artifact bytes, capture-entry/call
identity and provenance before injecting this descriptor. String hashes inside
JavaScript are not independent evidence of file contents. The actual capture
is not bundled here; no runnable fixture or placeholder payload is supplied here.

The wrapper reuses unchanged `prepareCapturedPracticeFixture` and original
snapshot reconstruction code. That historical function name describes the
first caller; its construction logic is parameterized by the captured fields,
wave and native conversion readbacks. This wrapper changes no field or expected
stat. The fixed ShootingRange mode validator remains unchanged. Existing typed
host-output callback receipts remain required and exact scene replay remains
false. Separate expected native conversion values verify construction; they do
not become constructor arguments or expected combat outcomes.

The result adds `modeInput`, capture/provenance identities and a raid-group
getter readback. `createOriginal153KrakenProcess(runtime, staticImage, management,
pin, emit, modeInput, fixture)` requires that result. It does not install the
static transporter, initialize management, load geometry, schedule ticks or
start a battle. The parent must preserve original loading order separately.

Before the original process calls, supply frozen `KRAKEN153_MODE_BINDING` from
`kraken-mode-binding153.json` and independently bind its file hash. Full current
native entry bodies425/235bytes, method signatures, class size136 and parent
are checked. The call order is original Intercept constructor0712D170, manager
SetProcess07607310, then original Intercept override CreateContext0712D080.
The override itself calls Campaign.CreateContext and owns Intercept setup; it
must not be replaced with a parent-only call. Original constructor condition
lists `[1,0,2]` and `[]` are verified without writes.

The current table contract is `../kraken153-encounter-source.json` SHA
`c33edc642e1840ec116ccbc5f8405a406ce2efa99107789b2109aa9d5421fded`.
It selects wave6302009/process7/180seconds. Configured cover level8, character
limit400 and monster/dynamic250 are table facts, not claimed actual capture or
runtime-setting readbacks. Transporter process/team/stage values must come from
the new original capture. The captured transporter process value is explicitly
separate from process class7; it is never silently changed from0 to7.

Tests use synthetic ABI objects only. They execute these real modules and cover
capture provenance, ordered actor identity, unchanged argument ownership,
original call order, complete-entry guards, condition validation and preserved
native error identity. They do not emulate combat or prove native behavior.
