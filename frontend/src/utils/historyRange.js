export function clampBrushRange(range, length) {
  if (!length) return { startIndex: 0, endIndex: 0 };
  const lastIndex = length - 1;
  const first = Math.max(0, Math.min(lastIndex, Number(range?.startIndex ?? 0)));
  const last = Math.max(0, Math.min(lastIndex, Number(range?.endIndex ?? lastIndex)));
  return first <= last
    ? { startIndex: first, endIndex: last }
    : { startIndex: last, endIndex: first };
}

export function findBrushIndexes(points, start, end) {
  if (!points.length) return { startIndex: 0, endIndex: 0 };
  let startIndex = 0;
  let endIndex = points.length - 1;

  for (let index = 0; index < points.length; index += 1) {
    if (points[index].timestamp <= start) startIndex = index;
    if (points[index].timestamp >= end) {
      endIndex = index;
      break;
    }
  }
  return clampBrushRange({ startIndex, endIndex }, points.length);
}

export function toDateTimeInput(timestamp) {
  return timestamp ? timestamp.slice(0, 16) : '';
}
