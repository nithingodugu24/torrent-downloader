import { useDialog } from './useDialog';
import {
  Check,
  Copy,
  Files,
  Pause,
  Play,
  Save,
  Square,
  Tv,
  X
} from 'lucide-react';
import { FormEvent, useEffect, useRef, useState } from 'react';
import type {
  TaskEvent,
  TorrentFile,
  TorrentPatch,
  TorrentTask
} from '../api/types';
import { formatBytes, formatPercent, formatSpeed } from '../utils/format';
import { LogPanel } from './LogPanel';
import { prepareStream } from '../api/client';

interface DetailDrawerProps {
  task: TorrentTask | null;
  events: TaskEvent[];
  files: TorrentFile[];
  onClose: () => void;
  onAction: (id: string, action: string) => Promise<void>;
  onPatch: (id: string, patch: TorrentPatch) => Promise<void>;
  loading: boolean;
  loadError: string | null;
  pendingAction?: string;
}

export function DetailDrawer({
  task,
  events,
  files,
  loading,
  loadError,
  pendingAction,
  onClose,
  onAction,
  onPatch
}: DetailDrawerProps) {
  const drawerRef = useRef<HTMLElement>(null);
  const [category, setCategory] = useState('');
  const [priority, setPriority] = useState(4);
  const [downloadLimit, setDownloadLimit] = useState('');
  const [uploadLimit, setUploadLimit] = useState('');
  const [maxConnections, setMaxConnections] = useState('');
  const [sequential, setSequential] = useState(false);
  const [stream, setStream] = useState<{ url: string; name: string } | null>(
    null
  );
  const [streamBusy, setStreamBusy] = useState(false);
  const [streamMessage, setStreamMessage] = useState('');
  const [view, setView] = useState<'overview' | 'files' | 'activity'>(
    'overview'
  );
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [actionError, setActionError] = useState('');
  const [saveError, setSaveError] = useState('');

  useEffect(() => {
    setStream(null);
    setStreamMessage('');
  }, [task?.id]);

  useEffect(() => {
    if (!task) return;
    setCategory(task.category ?? '');
    setPriority(task.priority);
    setDownloadLimit(task.download_limit ? String(task.download_limit) : '');
    setUploadLimit(task.upload_limit ? String(task.upload_limit) : '');
    setMaxConnections(task.max_connections ? String(task.max_connections) : '');
    setSequential(task.is_sequential);
  }, [
    task?.id,
    task?.category,
    task?.priority,
    task?.download_limit,
    task?.upload_limit,
    task?.max_connections,
    task?.is_sequential
  ]);

  useDialog(drawerRef, Boolean(task), onClose);

  if (!task) {
    return null;
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setFeedback('');
    setSaveError('');
    try {
      await onPatch(task.id, {
        category: category || null,
        priority,
        download_limit: downloadLimit ? Number(downloadLimit) : null,
        upload_limit: uploadLimit ? Number(uploadLimit) : null,
        max_connections: maxConnections ? Number(maxConnections) : null,
        is_sequential: sequential
      });
      setFeedback('Settings saved.');
    } catch (err) {
      setSaveError(
        err instanceof Error
          ? err.message
          : 'Unable to save settings. Try again.'
      );
    } finally {
      setSaving(false);
    }
  };
  const action = async (name: string) => {
    setActionError('');
    setFeedback('');
    try {
      await onAction(task.id, name);
    } catch (err) {
      setActionError(
        err instanceof Error
          ? err.message
          : 'Unable to update transfer. Try again.'
      );
    }
  };

  const startStream = async (file: TorrentFile) => {
    setStreamBusy(true);
    setStreamMessage('');
    try {
      const url = await prepareStream(task.id, file.index);
      setStream({ url, name: file.path });
    } catch (error) {
      setStreamMessage(
        error instanceof Error ? error.message : 'Unable to prepare stream.'
      );
    } finally {
      setStreamBusy(false);
    }
  };
  const videos = files.filter((file) => file.stream_url);
  const mainVideo = [...videos].sort((a, b) => b.size - a.size)[0];

  return (
    <aside
      ref={drawerRef}
      className="detail-drawer"
      role="dialog"
      aria-modal="true"
      aria-label="Transfer details"
    >
      <div className="detail-header">
        <div>
          <h2>{task.name || 'Metadata pending'}</h2>
          <span className={`status-chip ${task.status}`}>{task.status}</span>
        </div>
        <button
          className="icon-button"
          type="button"
          onClick={onClose}
          title="Close details"
          aria-label="Close details"
        >
          <X size={18} aria-hidden="true" />
        </button>
      </div>
      <div className="drawer-tabs" aria-label="Detail sections">
        {(['overview', 'files', 'activity'] as const).map((tab) => (
          <button
            key={tab}
            type="button"
            aria-pressed={view === tab}
            className={view === tab ? 'active' : ''}
            onClick={() => setView(tab)}
          >
            {tab === 'files'
              ? `Files (${files.length})`
              : tab === 'overview'
                ? 'Overview'
                : 'Activity'}
          </button>
        ))}
      </div>
      {actionError && (
        <div className="error-banner" role="alert">
          {actionError}
        </div>
      )}
      {loadError && (
        <div className="error-banner" role="alert">
          {loadError} Retrying automatically.
        </div>
      )}
      {view === 'overview' && (
        <>
          <div className="stats-grid">
            <Metric label="Progress" value={formatPercent(task.progress)} />
            <Metric label="Downloaded" value={formatBytes(task.downloaded)} />
            <Metric label="Ratio" value={task.ratio.toFixed(2)} />
            <Metric label="Uploaded" value={formatBytes(task.uploaded)} />
            <Metric
              label="Down speed"
              value={formatSpeed(task.download_speed)}
            />
            <Metric label="Up speed" value={formatSpeed(task.upload_speed)} />
            <Metric
              label="Peers / seeds"
              value={`${task.peers}/${task.seeds}`}
            />
          </div>
          {task.error_message && (
            <div className="error-banner">{task.error_message}</div>
          )}
          <div className="drawer-actions">
            <button
              disabled={Boolean(pendingAction)}
              onClick={() => action('resume')}
              title="Resume"
            >
              <Play size={16} aria-hidden="true" />
              Resume
            </button>
            <button
              disabled={Boolean(pendingAction)}
              onClick={() => action('pause')}
              title="Pause"
            >
              <Pause size={16} aria-hidden="true" />
              Pause
            </button>
            <button
              disabled={Boolean(pendingAction)}
              onClick={() => action('stop')}
              title="Stop"
            >
              <Square size={16} aria-hidden="true" />
              Stop
            </button>
          </div>
          {pendingAction && (
            <p className="inline-feedback" role="status">
              Updating transfer...
            </p>
          )}
          <section className="stream-section">
            <h3>
              <Tv size={18} /> Watch while downloading
            </h3>
            <p className="stream-help">
              Prepare a video link for VLC. The torrent keeps downloading during
              playback.
            </p>
            <button
              className="primary-button"
              disabled={!mainVideo || streamBusy}
              onClick={() => startStream(mainVideo)}
            >
              <Tv size={17} aria-hidden="true" />
              {streamBusy ? 'Buffering video...' : 'Stream in VLC'}
            </button>

            {streamBusy && (
              <p role="status">
                Downloading the first video buffer. The stream URL will appear
                when it is ready to play.
              </p>
            )}
            {!files.length && !loadError && (
              <p>
                {loading
                  ? 'Loading video files...'
                  : 'Waiting for torrent metadata to find video files...'}
              </p>
            )}
            {!!files.length && !videos.length && (
              <p>No supported video files in this torrent.</p>
            )}
            {stream && (
              <>
                <strong className="stream-name">{stream.name}</strong>
                <label className="field">
                  VLC stream URL
                  <input
                    readOnly
                    value={stream.url}
                    onFocus={(event) => event.target.select()}
                  />
                </label>
                <button
                  type="button"
                  onClick={async () => {
                    try {
                      await navigator.clipboard.writeText(stream.url);
                      setStreamMessage('URL copied.');
                    } catch {
                      setStreamMessage(
                        'Select the URL above and copy it manually.'
                      );
                    }
                  }}
                >
                  <Copy size={15} />
                  Copy stream URL
                </button>
                <p>
                  In VLC, press Ctrl+N, paste this URL and select Play. Playback
                  may buffer while downloading. Keep the torrent running.
                </p>
              </>
            )}
            {streamMessage && <p role="status">{streamMessage}</p>}
          </section>
          <details className="transfer-settings">
            <summary>
              Transfer settings<span>Category, bandwidth &amp; priority</span>
            </summary>
            <form className="settings-form" onSubmit={submit}>
              <label className="field">
                Category
                <input
                  value={category}
                  onChange={(event) => setCategory(event.target.value)}
                />
              </label>
              <div className="form-grid">
                <label className="field">
                  Priority
                  <input
                    type="number"
                    min="0"
                    max="7"
                    value={priority}
                    onChange={(event) =>
                      setPriority(Number(event.target.value))
                    }
                  />
                </label>
                <label className="field">
                  Download cap (B/s)
                  <input
                    type="number"
                    min="0"
                    placeholder="Unlimited"
                    value={downloadLimit}
                    onChange={(event) => setDownloadLimit(event.target.value)}
                  />
                </label>
                <label className="field">
                  Upload cap (B/s)
                  <input
                    type="number"
                    min="0"
                    placeholder="Unlimited"
                    value={uploadLimit}
                    onChange={(event) => setUploadLimit(event.target.value)}
                  />
                </label>
                <label className="field">
                  Connections
                  <input
                    type="number"
                    min="0"
                    placeholder="Default"
                    value={maxConnections}
                    onChange={(event) => setMaxConnections(event.target.value)}
                  />
                </label>
              </div>
              <label className="check-field">
                <input
                  type="checkbox"
                  checked={sequential}
                  onChange={(event) => setSequential(event.target.checked)}
                />
                Sequential download
              </label>
              <button
                className="primary-button"
                type="submit"
                disabled={saving}
              >
                <Save size={16} aria-hidden="true" />
                {saving ? 'Saving...' : 'Save settings'}
              </button>
              {saveError && (
                <div className="error-banner" role="alert">
                  {saveError}
                </div>
              )}
              {feedback && (
                <p className="success-feedback" role="status">
                  <Check size={16} />
                  {feedback}
                </p>
              )}
            </form>
          </details>
        </>
      )}
      {view === 'files' && (
        <section className="files-section">
          <h3>
            <Files size={17} /> Torrent files
          </h3>
          {loading && (
            <p className="section-note" role="status">
              Loading files...
            </p>
          )}
          {!loading && !files.length && !loadError && (
            <p className="section-note">
              Files will appear when torrent metadata is available.
            </p>
          )}
          <div className="file-list">
            {files.slice(0, 1000).map((file) => (
              <div className="file-row" key={file.index}>
                <div>
                  <strong title={file.path}>{file.path}</strong>
                  <span>{formatBytes(file.size)}</span>
                </div>
                <span>{formatPercent(file.progress)}</span>
                <div className="file-actions">
                  {file.download_url && (
                    <a href={file.download_url}>Download</a>
                  )}
                  {file.stream_url && (
                    <button
                      disabled={streamBusy}
                      onClick={() =>
                        startStream(file).then(() => setView('overview'))
                      }
                    >
                      Stream
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
      {view === 'activity' && <LogPanel events={events} loading={loading} />}
    </aside>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
