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

function formatLocalDateTime(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hour = String(date.getHours()).padStart(2, '0');
  const minute = String(date.getMinutes()).padStart(2, '0');
  return `${year}-${month}-${day}T${hour}:${minute}`;
}

export function getPresetRange(latestTimestamp, days) {
  const end = new Date(latestTimestamp);
  const start = new Date(end.getTime() - days * 24 * 60 * 60 * 1000);
  return { start: formatLocalDateTime(start), end: formatLocalDateTime(end) };
}

export function coversFullRange(selection, oldest, latest) {
  return selection.start <= toDateTimeInput(oldest)
    && selection.end >= toDateTimeInput(latest);
}
