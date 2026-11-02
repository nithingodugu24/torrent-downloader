import {
  Download,
  File,
  MoreHorizontal,
  Pause,
  Play,
  Plus,
  RotateCcw,
  Square,
  Trash2,
  Tv
} from 'lucide-react';
import type { TorrentTask } from '../api/types';
import { formatBytes, formatPercent, formatSpeed } from '../utils/format';

interface TaskTableProps {
  tasks: TorrentTask[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onAction: (id: string, action: string) => void;
  onAdd: () => void;
  filtered: boolean;
  loading: boolean;
  failed: boolean;
  pendingActions: Record<string, string>;
  onClearFilters: () => void;
}

export function TaskTable({
  tasks,
  selectedId,
  onSelect,
  onAction,
  onAdd,
  filtered,
  loading,
  failed,
  pendingActions,
  onClearFilters
}: TaskTableProps) {
  if (loading)
    return (
      <div className="loading-state" role="status">
        <span className="loading-line" />
        <span className="loading-line" />
        <span className="loading-line" />
        <p>Loading transfers...</p>
      </div>
    );
  if (failed && !tasks.length)
    return (
      <div className="empty-state">
        <h3>Transfers couldn't be loaded</h3>
        <p>
          Check that the local server is running, then refresh to try again.
        </p>
      </div>
    );
  if (!tasks.length)
    return (
      <div className="empty-state">
        <Download size={32} strokeWidth={1.5} aria-hidden="true" />
        <h3>
          {filtered
            ? 'No matching transfers'
            : 'Your next download starts here'}
        </h3>
        <p>
          {filtered
            ? 'Try another search or choose a different status.'
            : 'Add a magnet link or a .torrent file to get started.'}
        </p>
        {filtered && (
          <button className="ghost-button" onClick={onClearFilters}>
            Clear filters
          </button>
        )}
        {!filtered && (
          <button className="primary-button" onClick={onAdd}>
            <Plus size={17} />
            Add torrent
          </button>
        )}
      </div>
    );

  return (
    <div className="table-wrap">
      <table className="task-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Status</th>
            <th>Progress</th>
            <th>Download</th>
            <th>Upload</th>
            <th>Size</th>
            <th>
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {tasks.map((task) => (
            <tr
              key={task.id}
              className={task.id === selectedId ? 'selected' : ''}
            >
              <td className="name-cell">
                <button
                  className="task-select"
                  aria-label={`View details for ${task.name || 'Metadata pending'}`}
                  onClick={() => onSelect(task.id)}
                >
                  <span className="file-icon">
                    <File size={19} />
                  </span>
                  <span className="task-label">
                    <span className="task-name" title={task.name}>
                      {task.name || 'Metadata pending'}
                    </span>
                    <span className="task-subline">
                      {task.category || 'Uncategorized'} / {task.peers} peers /{' '}
                      {task.seeds} seeds
                    </span>
                  </span>
                </button>
              </td>
              <td data-label="Status">
                <span className={`status-chip ${task.status}`}>
                  {task.status}
                </span>
              </td>
              <td data-label="Progress">
                <div className="progress-cell">
                  <span>{formatPercent(task.progress)}</span>
                  <div
                    className="progress-track"
                    role="progressbar"
                    aria-label={`${task.name} progress`}
                    aria-valuenow={Math.round(task.progress * 100)}
                    aria-valuemin={0}
                    aria-valuemax={100}
                  >
                    <div
                      className={`progress-fill ${task.status}`}
                      style={{
                        width: `${Math.min(100, Math.max(0, task.progress * 100))}%`
                      }}
                    />
                  </div>
                </div>
              </td>
              <td data-label="Download" className="speed-cell">
                {formatSpeed(task.download_speed)}
              </td>
              <td data-label="Upload" className="speed-cell">
                {formatSpeed(task.upload_speed)}
              </td>
              <td data-label="Size">{formatBytes(task.total_size)}</td>
              <td className="actions-cell">
                <div
                  className="row-actions"
                  aria-busy={Boolean(pendingActions[task.id])}
                >
                  <button
                    aria-label={`Streaming options for ${task.name}`}
                    title="Show VLC streaming options"
                    onClick={() => onSelect(task.id)}
                  >
                    <Tv size={16} />
                  </button>
                  {['paused', 'stopped', 'errored', 'queued'].includes(
                    task.status
                  ) ? (
                    <button
                      disabled={Boolean(pendingActions[task.id])}
                      aria-label={`Resume ${task.name}`}
                      title="Resume"
                      onClick={() => onAction(task.id, 'resume')}
                    >
                      <Play size={16} />
                    </button>
                  ) : (
                    <button
                      disabled={Boolean(pendingActions[task.id])}
                      aria-label={`Pause ${task.name}`}
                      title="Pause"
                      onClick={() => onAction(task.id, 'pause')}
                    >
                      <Pause size={16} />
                    </button>
                  )}
                  <details
                    className="action-menu"
                    onKeyDown={(event) => {
                      if (event.key === 'Escape') {
                        event.currentTarget.removeAttribute('open');
                        event.currentTarget
                          .querySelector<HTMLElement>('summary')
                          ?.focus();
                      }
                    }}
                    onBlur={(event) => {
                      if (
                        !event.currentTarget.contains(
                          event.relatedTarget as Node
                        )
                      )
                        event.currentTarget.removeAttribute('open');
                    }}
                    onToggle={(event) => {
                      if (event.currentTarget.open)
                        document
                          .querySelectorAll<HTMLDetailsElement>(
                            '.action-menu[open]'
                          )
                          .forEach((menu) => {
                            if (menu !== event.currentTarget) menu.open = false;
                          });
                    }}
                  >
                    <summary aria-label={`More actions for ${task.name}`}>
                      <MoreHorizontal size={18} />
                    </summary>
                    <div>
                      <button
                        disabled={Boolean(pendingActions[task.id])}
                        onClick={(event) => {
                          onAction(task.id, 'stop');
                          event.currentTarget
                            .closest('details')
                            ?.removeAttribute('open');
                        }}
                      >
                        <Square size={15} />
                        Stop transfer
                      </button>
                      <button
                        disabled={Boolean(pendingActions[task.id])}
                        onClick={(event) => {
                          onAction(task.id, 'recheck');
                          event.currentTarget
                            .closest('details')
                            ?.removeAttribute('open');
                        }}
                      >
                        <RotateCcw size={15} />
                        Recheck files
                      </button>
                      <button
                        disabled={Boolean(pendingActions[task.id])}
                        className="danger-action"
                        onClick={() => onAction(task.id, 'remove')}
                      >
                        <Trash2 size={15} />
                        Remove transfer
                      </button>
                    </div>
                  </details>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
