'use strict';
// Execute the real page source with a small DOM and queued HTTP responses.
// These controls never start a server, broker or native process.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, 'web/native-practice.js'), 'utf8');
const key = 'raid-lab-native-practice-job';
const id = '1234567890abcdef12345678';
const result = {score: '9007199254740993', characters: [{tableId: 301701, damage: '9007199254740993'}]};
const ok = value => ({ok: true, status: 200, json: async () => value});
const rejected = (status, error) => ({ok: false, status, json: async () => ({error})});
const flush = () => new Promise(resolve => setImmediate(resolve));
function page(replies, saved = null) {
  const elements = new Map(), storage = new Map(saved ? [[key, saved]] : []);
  const requests = [], timers = [], downloads = [], blobs = [];
  function element(name) {
    if (!elements.has(name)) elements.set(name, {
      textContent: name === 'native-run' ? 'Run original engine' : '', hidden: false, disabled: false,
      children: [], handlers: {}, addEventListener(event, fn) { this.handlers[event] = fn; },
      replaceChildren(...rows) { this.children = rows; }, append(row) { this.children.push(row); },
      click() { downloads.push({href: this.href, download: this.download}); }
    });
    return elements.get(name);
  }
  const context = {
    document: {getElementById: element, createElement: name => ({children: [], append(row) {this.children.push(row);}, click() {downloads.push({href: this.href, download: this.download});}})},
    sessionStorage: {getItem: name => storage.get(name) || null, setItem: (name, value) => storage.set(name, value), removeItem: name => storage.delete(name)},
    fetch: async (url, options = {}) => {
      requests.push({url, options});
      assert.ok(replies.length, 'Unexpected HTTP call: ' + url);
      const next = replies.shift();
      if (next instanceof Error) throw next;
      return typeof next === 'function' ? next(url, options) : next;
    },
    setTimeout: fn => timers.push(fn),
    Blob: class { constructor(parts, options) {blobs.push({parts, options});} },
    URL: {createObjectURL: () => 'blob:test', revokeObjectURL() {}},
    BigInt, Map, JSON, Error, String
  };
  vm.runInNewContext(source, context, {filename: 'native-practice.js'});
  return {elements, storage, requests, timers, downloads, blobs,
    get: element, click: name => element(name).handlers.click(),
    tick: async () => {assert.ok(timers.length); await timers.shift()(); await flush();}};
}
let passed = 0;
async function check(fn) {await fn(); passed++;}
(async () => {
  await check(async () => {
    const p = page([ok({id}), ok({status: 'error', error: 'Native gate failed'}), ok({id}), ok({status: 'cancelled'})]);
    await p.click('native-run');
    assert.equal(p.storage.has(key), false); assert.equal(p.get('native-run').disabled, false);
    assert.equal(p.get('native-error').textContent, 'Native gate failed');
    assert.match(p.get('native-status').textContent, /try again/);
    await p.click('native-run'); assert.equal(p.requests.filter(x => x.options.method === 'POST').length, 2);
    assert.match(p.get('native-status').textContent, /Cancelled/);
  });
  await check(async () => {
    const p = page([ok({id}), new Error('offline'), ok({status: 'done', result})]);
    await p.click('native-run');
    assert.equal(p.storage.get(key), id); assert.equal(p.get('native-run').textContent, 'Reconnect to job');
    assert.equal(p.get('native-run').disabled, false);
    await p.click('native-run');
    assert.equal(p.requests.filter(x => x.options.method === 'POST').length, 1);
    assert.equal(p.storage.has(key), false); assert.equal(p.get('native-result').hidden, false);
    assert.equal(p.get('native-score').textContent.replace(/\D/g, ''), result.score);
  });
  await check(async () => {
    const p = page([ok({status: 'running', phase: 'Playing'}), ok({status: 'done', result})], id);
    await flush(); assert.equal(p.requests[0].url, '/api/jobs/' + id);
    assert.equal(p.requests.some(x => x.options.method === 'POST'), false);
    await p.tick(); assert.match(p.get('native-status').textContent, /complete/);
  });
  await check(async () => {
    const p = page([new Error('response lost'), ok({job: {id, status: 'running'}}), ok({status: 'running'}), ok({status: 'done', result})]);
    await p.click('native-run'); assert.equal(p.storage.get(key), 'pending-start');
    assert.match(p.get('native-status').textContent, /may be running/);
    assert.doesNotMatch(p.get('native-status').textContent, /not started/);
    await p.click('native-run'); assert.equal(p.requests[1].url, '/api/native/practice/status');
    assert.equal(p.requests.filter(x => x.options.method === 'POST').length, 1);
    assert.match(p.get('native-status').textContent, /Recovered latest/);
    await p.tick(); assert.match(p.get('native-status').textContent, /Recovered latest.*complete/);
  });
  await check(async () => {
    const p = page([ok({job: null}), ok({id}), ok({status: 'cancelled'})], 'pending-start');
    await flush(); assert.equal(p.storage.has(key), false); assert.equal(p.requests.length, 1);
    assert.equal(p.get('native-run').disabled, false); assert.match(p.get('native-status').textContent, /explicitly retry/);
    await p.click('native-run'); assert.equal(p.requests.filter(x => x.options.method === 'POST').length, 1);
  });
  await check(async () => {
    const p = page([new Error('status unavailable'), ok({job: null})], 'pending-start');
    await flush(); assert.equal(p.storage.get(key), 'pending-start');
    assert.equal(p.get('native-run').textContent, 'Check start status');
    await p.click('native-run'); assert.equal(p.requests.some(x => x.options.method === 'POST'), false);
    assert.equal(p.storage.has(key), false);
  });
  await check(async () => {
    const p = page([rejected(503, 'Unavailable'), ok({job: null})]);
    await p.click('native-run'); assert.equal(p.storage.get(key), 'pending-start');
    await p.click('native-run'); assert.equal(p.requests[1].url, '/api/native/practice/status');
  });
  await check(async () => {
    const p = page([rejected(400, 'Unsupported fixture')]);
    await p.click('native-run'); assert.equal(p.storage.has(key), false);
    assert.equal(p.get('native-run').disabled, false); assert.match(p.get('native-status').textContent, /rejected/);
  });
  await check(async () => {
    const p = page([ok({id: 'bad'}), ok({job: null})]);
    await p.click('native-run'); assert.equal(p.storage.get(key), 'pending-start');
    await p.click('native-run'); assert.equal(p.requests.filter(x => x.options.method === 'POST').length, 1);
  });
  await check(async () => {
    let release;
    const p = page([() => new Promise(resolve => {release = resolve;}), ok({status: 'cancelled'})]);
    const first = p.click('native-run'); await flush(); await p.click('native-run');
    assert.equal(p.requests.length, 1); release(ok({id})); await first;
  });
  await check(async () => {
    const p = page([ok({id}), ok({status: 'running'}), ok({status: 'cancelling'}), ok({status: 'cancelled'})]);
    await p.click('native-run'); await p.click('native-cancel');
    assert.equal(p.requests[2].url, '/api/cancel/' + id);
    assert.equal(p.get('native-cancel').disabled, false); assert.match(p.get('native-status').textContent, /Waiting/);
    await p.tick(); assert.equal(p.storage.has(key), false); assert.equal(p.get('native-cancel').hidden, true);
  });
  await check(async () => {
    const p = page([ok({id}), ok({status: 'done', result})]); await p.click('native-run');
    await p.click('native-export');
    assert.equal(p.downloads[0].download, 'original-engine-practice.json');
    assert.equal(JSON.parse(p.blobs[0].parts[0]).score, '9007199254740993');
  });
  await check(async () => {
    const p = page([ok({status: 'unexpected'}), ok({status: 'error', error: 'Stopped'})], id);
    await flush(); assert.equal(p.storage.get(key), id); assert.equal(p.get('native-run').textContent, 'Reconnect to job');
    await p.click('native-run'); assert.equal(p.storage.has(key), false);
  });
  console.log(`${passed} actual native-practice page lifecycle controls PASS; mocked DOM/HTTP only`);
})().catch(error => {console.error(error); process.exitCode = 1;});
