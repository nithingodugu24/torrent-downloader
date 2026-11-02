import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import ts from 'typescript';

const source = await readFile(new URL('../src/utils/loadProviders.ts', import.meta.url), 'utf8');
const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } });
const { loadProviders } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`);
const deferred = () => {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return { promise, resolve };
};

test('fast results are published while a slow source remains unresolved', async () => {
  const slow = deferred();
  const firstResult = deferred();
  const received = [];
  let finished = false;
  const loading = loadProviders(['slow', 'fast'],
    name => name === 'slow' ? slow.promise : Promise.resolve(['fast result']),
    (name, result) => { received.push([name, result]); firstResult.resolve(); },
    () => assert.fail('unexpected provider failure'), new AbortController().signal
  ).then(() => { finished = true; });
  await firstResult.promise;
  assert.deepEqual(received, [['fast', ['fast result']]]);
  assert.equal(finished, false);
  slow.resolve(['slow result']);
  await loading;
  assert.deepEqual(received.map(([name]) => name), ['fast', 'slow']);
});

test('one failed source leaves other results usable', async () => {
  const results = [];
  const failures = [];
  await loadProviders(['failed', 'good'],
    async name => { if (name === 'failed') throw new Error('offline'); return ['usable']; },
    (name, result) => results.push([name, result]),
    (name, error) => failures.push([name, error.message]), new AbortController().signal);
  assert.deepEqual(results, [['good', ['usable']]]);
  assert.deepEqual(failures, [['failed', 'offline']]);
});

test('stopped or replaced searches cannot publish late results', async () => {
  const pending = deferred();
  const controller = new AbortController();
  const loading = loadProviders(['old'], () => pending.promise,
    () => assert.fail('stale results were published'),
    () => assert.fail('stale errors were published'), controller.signal);
  controller.abort();
  pending.resolve(['old result']);
  await loading;
});

test('already aborted searches do not start requests', async () => {
  const controller = new AbortController(); controller.abort();
  await loadProviders(['source'], () => assert.fail('request started'),
    () => assert.fail('result published'), () => assert.fail('error published'), controller.signal);
});
