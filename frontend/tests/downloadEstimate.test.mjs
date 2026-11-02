import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import ts from 'typescript';
const source = await readFile(new URL('../src/utils/downloadEstimate.ts', import.meta.url), 'utf8');
const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } });
const { estimateRemaining, formatDownloadTime, parseTorrentSize, estimateSearchTime, transferConnection } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`);
const snapshot = (overrides = {}) => ({ status:'downloading', total_size:1000000, downloaded:400000, download_speed:10000, progress:0.4, seeds:3, peers:5, ...overrides });

test('ETA uses remaining bytes and measured speed, rather than total size', () => {
  assert.equal(estimateRemaining(snapshot()), 'About 1 min left');
  assert.equal(estimateRemaining(snapshot({downloaded:500000,download_speed:100000})), 'Less than a minute left');
});
test('no invented ETA while paused, gathering metadata, queued or stalled', () => {
  assert.equal(estimateRemaining(snapshot({status:'metadata',total_size:0})), 'Waiting for file details');
  assert.equal(estimateRemaining(snapshot({status:'paused'})), 'Paused');
  assert.equal(estimateRemaining(snapshot({status:'queued'})), 'Queued');
  assert.equal(estimateRemaining(snapshot({download_speed:0})), 'Waiting for data');
  assert.equal(estimateRemaining(snapshot({download_speed:NaN})), 'Waiting for data');
  assert.equal(estimateRemaining(snapshot({total_size:0})), 'Waiting for file details');
});
test('completed data is complete even when upload continues', () => {
  assert.equal(estimateRemaining(snapshot({status:'seeding'})), 'Complete');
  assert.equal(estimateRemaining(snapshot({downloaded:1000000})), 'Complete');
});
test('time rounding and units remain readable at hour and day boundaries', () => {
  assert.equal(formatDownloadTime(3599), 'About 1 hr');
  assert.equal(formatDownloadTime(3661), 'About 1 hr 2 min');
  assert.equal(formatDownloadTime(90000), 'About 1 day 1 hr');
  assert.equal(formatDownloadTime(Infinity), 'Not enough data');
});
test('search sizes distinguish binary and decimal units and ignore missing data', () => {
  assert.equal(parseTorrentSize('1 GiB'), 1073741824);
  assert.equal(parseTorrentSize('1 GB'), 1000000000);
  assert.equal(parseTorrentSize('1,024 KB'), 1024000);
  assert.equal(parseTorrentSize('n/a'), null);
  assert.equal(parseTorrentSize(null), null);
});
test('pre-download estimates use entered Mbps without assuming a speed', () => {
  assert.equal(estimateSearchTime('1 GB',100), 'About 2 min');
  assert.equal(estimateSearchTime('1 GB',0), 'Estimate after starting');
  assert.equal(estimateSearchTime(null,100), 'Size unknown');
  assert.equal(estimateSearchTime('1 GB',-10), 'Estimate after starting');
});
test('live signal distinguishes metadata, receiving pieces and stalled peers', () => {
  assert.equal(transferConnection(snapshot({status:'metadata'})).bars, null);
  assert.equal(transferConnection(snapshot()).bars,4);
  assert.equal(transferConnection(snapshot({seeds:0})).bars,2);
  assert.equal(transferConnection(snapshot({seeds:0,peers:0,download_speed:0})).bars,0);
  assert.equal(transferConnection(snapshot({seeds:0,peers:2,download_speed:0})).bars,1);
  assert.equal(transferConnection(snapshot({seeds:2,download_speed:0})).bars,3);
  assert.equal(transferConnection(snapshot({status:'paused'})).bars,null);
});
