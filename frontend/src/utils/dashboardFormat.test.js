import test from 'node:test';
import assert from 'node:assert/strict';

import { formatChartTimestamp } from './dashboardFormat.js';

test('chart timestamps include both the date and time', () => {
  const label = formatChartTimestamp('2026-07-28T10:05:00');

  assert.match(label, /07\/28/);
  assert.match(label, /10:05/);
});
