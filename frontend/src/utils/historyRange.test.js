import test from 'node:test';
import assert from 'node:assert/strict';

import { clampBrushRange, findBrushIndexes } from './historyRange.js';

test('a narrowed brush range can expand back to the full navigator', () => {
  assert.deepEqual(clampBrushRange({ startIndex: 20, endIndex: 40 }, 100), {
    startIndex: 20,
    endIndex: 40,
  });
  assert.deepEqual(clampBrushRange({ startIndex: 0, endIndex: 99 }, 100), {
    startIndex: 0,
    endIndex: 99,
  });
});

test('direct dates map to the nearest available navigator points', () => {
  const points = [
    { timestamp: '2026-01-01T00:00:00' },
    { timestamp: '2026-01-02T00:00:00' },
    { timestamp: '2026-01-03T00:00:00' },
    { timestamp: '2026-01-04T00:00:00' },
  ];

  assert.deepEqual(
    findBrushIndexes(points, '2026-01-02T12:00:00', '2026-01-03T12:00:00'),
    { startIndex: 1, endIndex: 3 },
  );
});
