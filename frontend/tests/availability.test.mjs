import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import ts from 'typescript';

const source = await readFile(new URL('../src/utils/availability.ts', import.meta.url), 'utf8');
const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } });
const { estimateAvailability: estimate } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`);

test('missing counts do not imply a dead torrent', () => {
  for (const seeds of [null, -1, NaN, Infinity]) assert.equal(estimate(seeds, 100).tone, 'unknown');
});
test('no reported complete copies warns that completion is uncertain', () => {
  assert.equal(estimate(0, 100).label, 'May not finish');
  assert.equal(estimate(0, 0).tone, 'poor');
});
test('few complete copies remain limited even without competition', () => {
  for (const seeds of [1, 4]) assert.equal(estimate(seeds, 0).label, 'May be slow');
});
test('availability thresholds and heavy demand affect outlook', () => {
  assert.equal(estimate(5, 0).label, 'Available');
  assert.equal(estimate(19, null).label, 'Available');
  assert.equal(estimate(20, null).label, 'Well shared');
  assert.equal(estimate(20, 200).label, 'Well shared');
  assert.equal(estimate(20, 201).label, 'Busy · may be slow');
});
test('sort ranks prefer well shared results and leave unknown ahead of no copies', () => {
  const counts = [[0, 0], [null, null], [2, 0], [10, 200], [10, 0], [50, 0]];
  assert.deepEqual(counts.map(([seeds, peers]) => estimate(seeds, peers).rank), [0, 1, 2, 3, 4, 5]);
});

test('signal strength covers unknown, empty, weak, busy and well-shared sources', () => {
  assert.equal(estimate(null,10).bars,null);
  assert.equal(estimate(0,10).bars,0);
  assert.equal(estimate(1,0).bars,1);
  assert.equal(estimate(10,101).bars,2);
  assert.equal(estimate(5,0).bars,3);
  assert.equal(estimate(20,0).bars,4);
});
