export type TorrentStatus =
  | 'queued'
  | 'metadata'
  | 'downloading'
  | 'seeding'
  | 'paused'
  | 'completed'
  | 'errored'
  | 'stopped';

export interface TorrentTask {
  id: string;
  name: string;
  info_hash: string | null;
  magnet_uri: string | null;
  torrent_file_path: string | null;
  save_path: string;
  status: TorrentStatus;
  progress: number;
  download_speed: number;
  upload_speed: number;
  ratio: number;
  total_size: number;
  downloaded: number;
  uploaded: number;
  peers: number;
  seeds: number;
  priority: number;
  category: string | null;
  queue_position: number;
  is_sequential: boolean;
  download_limit: number | null;
  upload_limit: number | null;
  seed_limit: number | null;
  max_connections: number | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  error_message: string | null;
}

export interface TorrentFile {
  index: number;
  path: string;
  size: number;
  progress: number;
  priority: number;
  download_url: string | null;
  stream_url: string | null;
}

export interface TaskEvent {
  id: number;
  task_id: string | null;
  level: string;
  event_type: string;
  message: string;
  created_at: string;
}

export interface TorrentPatch {
  priority?: number;
  save_path?: string;
  category?: string | null;
  download_limit?: number | null;
  upload_limit?: number | null;
  seed_limit?: number | null;
  max_connections?: number | null;
  is_sequential?: boolean;
  queue_position?: number;
}

export interface TorrentUpdateMessage {
  event: string;
  task: Partial<TorrentTask> & { id: string };
}
