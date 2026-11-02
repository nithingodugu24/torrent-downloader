export function formatBytes(value: number): string {
  if (!value) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
  return `${(value / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

export function formatSpeed(value: number): string {
  return `${formatBytes(value)}/s`;
}

export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}
