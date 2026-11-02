import type { TaskEvent, TorrentFile, TorrentPatch, TorrentTask } from './types';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '';

export interface SearchResult {
  provider: 'bitsearch' | 'uindex' | 'limetorrents' | 'piratebay' | 'torrentdownload';
  title: string;
  url: string;
  size: string | null;
  seeds: number | null;
  leeches: number | null;
  magnet_uri: string | null;
}
export interface SearchResponse {
  results: SearchResult[];
  errors: Record<string, string>;
  page: number;
}
export function searchTorrents(q: string, provider: string, page: number, signal: AbortSignal): Promise<SearchResponse> {
  const params = new URLSearchParams({ q, page: String(page) });
  if (provider !== 'all') params.set('provider', provider);
  return request(`/api/search?${params}`, { signal });
}
export async function resolveSearchMagnet(result: SearchResult): Promise<string> {
  const response = await request<{ magnet_uri: string }>('/api/search/resolve', {
    method: 'POST', body: JSON.stringify({ provider: result.provider, url: result.url })
  });
  return response.magnet_uri;
}

export async function prepareStream(id: string, index: number): Promise<string> {
  for (let attempt = 0; attempt < 12; attempt++) {
    const result = await request<{ url?: string; ready: boolean }>(
      `/api/torrents/${id}/files/${index}/stream`, { method: 'POST' }
    );
    if (result.ready && result.url) {
      return new URL(`${API_BASE}${result.url}`, window.location.href).href;
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  throw new Error('Still buffering. Check download speed and seeds, then try Stream again.');
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: init?.body instanceof FormData ? undefined : { 'Content-Type': 'application/json' },
    ...init
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Request failed');
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export function websocketUrl(): string {
  if (import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL;
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/ws/torrents`;
}

export function listTorrents(params: URLSearchParams): Promise<TorrentTask[]> {
  const query = params.toString();
  return request<TorrentTask[]>(`/api/torrents${query ? `?${query}` : ''}`);
}

export function addMagnet(payload: {
  magnet_uri: string;
  save_path?: string;
  category?: string;
  priority: number;
  is_sequential: boolean;
}): Promise<TorrentTask> {
  return request<TorrentTask>('/api/torrents/magnet', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export function uploadTorrent(payload: {
  file: File;
  save_path?: string;
  category?: string;
  priority: number;
  is_sequential: boolean;
}): Promise<TorrentTask> {
  const form = new FormData();
  form.append('file', payload.file);
  form.append('priority', String(payload.priority));
  form.append('is_sequential', String(payload.is_sequential));
  if (payload.save_path) form.append('save_path', payload.save_path);
  if (payload.category) form.append('category', payload.category);
  return request<TorrentTask>('/api/torrents/file', { method: 'POST', body: form });
}

export function torrentAction(id: string, action: string): Promise<TorrentTask> {
  return request<TorrentTask>(`/api/torrents/${id}/${action}`, { method: 'POST' });
}

export function updateTorrent(id: string, payload: TorrentPatch): Promise<TorrentTask> {
  return request<TorrentTask>(`/api/torrents/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export function listFiles(id: string): Promise<TorrentFile[]> {
  return request<TorrentFile[]>(`/api/torrents/${id}/files`);
}

export function listEvents(id?: string): Promise<TaskEvent[]> {
  const query = id ? `?task_id=${encodeURIComponent(id)}` : '';
  return request<TaskEvent[]>(`/api/events${query}`);
}
