import type { TorrentTask } from '../api/types';

type TransferSnapshot = Pick<TorrentTask, 'status' | 'total_size' | 'downloaded' | 'download_speed' | 'progress' | 'seeds' | 'peers'>;

export function formatDownloadTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return 'Not enough data';
  if (seconds < 60) return 'Less than a minute';
  const minutes = Math.ceil(seconds / 60);
  if (minutes < 60) return `About ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const restMinutes = minutes % 60;
  if (hours < 24) return `About ${hours} hr${restMinutes ? ` ${restMinutes} min` : ''}`;
  const days = Math.floor(hours / 24);
  const restHours = hours % 24;
  return `About ${days} day${days === 1 ? '' : 's'}${restHours ? ` ${restHours} hr` : ''}`;
}

export function estimateRemaining(task: TransferSnapshot): string {
  if (['completed', 'seeding'].includes(task.status)) return 'Complete';
  if (task.status === 'paused') return 'Paused';
  if (task.status === 'stopped') return 'Stopped';
  if (task.status === 'errored') return 'Needs attention';
  if (task.status === 'queued') return 'Queued';
  if (task.status === 'metadata' || !Number.isFinite(task.total_size) || task.total_size <= 0) {
    return 'Waiting for file details';
  }
  if (!Number.isFinite(task.downloaded) || task.downloaded < 0) return 'Estimating…';
  if (task.downloaded >= task.total_size || task.progress >= 1) return 'Complete';
  if (!Number.isFinite(task.download_speed) || task.download_speed <= 0) return 'Waiting for data';
  return `${formatDownloadTime((task.total_size - task.downloaded) / task.download_speed)} left`;
}

export function parseTorrentSize(size: string | null): number | null {
  const match = size?.trim().match(/^([\d,]+(?:\.\d+)?)\s*(B|[KMGT]i?B|bytes)$/i);
  if (!match) return null;
  const number = Number(match[1].replaceAll(',', ''));
  const unit = match[2].toUpperCase();
  const exponent = Math.max(0, 'BKMGT'.indexOf(unit[0]));
  const bytes = number * (unit.includes('I') ? 1024 : 1000) ** exponent;
  return Number.isFinite(bytes) && bytes >= 0 ? bytes : null;
}

export function estimateSearchTime(size: string | null, mbps: number): string {
  const bytes = parseTorrentSize(size);
  if (bytes === null) return 'Size unknown';
  if (!Number.isFinite(mbps) || mbps <= 0) return 'Estimate after starting';
  return formatDownloadTime(bytes / (mbps * 1_000_000 / 8));
}

export function transferConnection(task: TransferSnapshot) {
  if (['completed', 'seeding'].includes(task.status)) return { bars: 4, label: 'Complete copy downloaded', tone: 'good' };
  if (['paused', 'stopped', 'queued'].includes(task.status)) return { bars: null, label: 'Not downloading', tone: 'unknown' };
  if (task.status === 'errored') return { bars: 0, label: 'Needs attention', tone: 'poor' };
  if (task.status === 'metadata') return { bars: null, label: 'Checking sources', tone: 'unknown' };
  if (task.download_speed > 0) return {
    bars: task.seeds > 0 ? 4 : 2,
    label: task.seeds > 0 ? 'Receiving data · full source connected' : 'Receiving pieces · no full source connected',
    tone: task.seeds > 0 ? 'good' : 'slow'
  };
  if (task.seeds > 0) return { bars: 3, label: 'Full source connected · waiting for data', tone: 'fair' };
  if (task.peers > 0) return { bars: 1, label: 'Peers connected · no full source yet', tone: 'slow' };
  return { bars: 0, label: 'No sources connected', tone: 'poor' };
}
