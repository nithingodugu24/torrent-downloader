import { useState } from 'react';
import {
  ArrowDown,
  ArrowUp,
  CheckCheck,
  Download,
  HardDrive,
  Layers3,
  Pause,
  ShieldCheck
} from 'lucide-react';
import { formatBytes, formatSpeed } from './utils/format';
import { AddTorrentModal } from './components/AddTorrentModal';
import { DetailDrawer } from './components/DetailDrawer';
import { GlobalControls } from './components/GlobalControls';
import { TaskTable } from './components/TaskTable';
import { TopBar } from './components/TopBar';
import { useTorrents } from './state/useTorrents';

export function App() {
  const torrents = useTorrents();
  const [isAddOpen, setAddOpen] = useState(false);

  const filters = [
    { value: '', label: 'All transfers', icon: Layers3 },
    { value: 'downloading', label: 'Downloading', icon: ArrowDown },
    { value: 'seeding', label: 'Seeding', icon: ArrowUp },
    { value: 'completed', label: 'Completed', icon: CheckCheck },
    { value: 'paused', label: 'Paused', icon: Pause }
  ];
  return (
    <div className="app-shell">
      <a className="skip-link" href="#transfers">
        Skip to transfers
      </a>
      <aside className="sidebar">
        <a className="brand-block" href="/" aria-label="Torrent Downloader home">
          <span className="brand-mark">
            <Download size={22} />
          </span>
          <span>
            Torrent Downloader<span className="brand-caption">TRANSFER MANAGER</span>
          </span>
        </a>
        <div className="nav-label">LIBRARY</div>
        <nav aria-label="Transfer filters">
          {filters.map(({ value, label, icon: Icon }) => (
            <button
              key={value}
              aria-current={
                torrents.statusFilter === value ? 'page' : undefined
              }
              className={`nav-item ${torrents.statusFilter === value ? 'active' : ''}`}
              onClick={() => torrents.setStatusFilter(value)}
            >
              <Icon size={18} />
              <span>{label}</span>
              <span className="nav-count">
                {
                  torrents.allTasks.filter(
                    (task) => !value || task.status === value
                  ).length
                }
              </span>
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <ShieldCheck size={18} />
          <div>
            Local workspace<span>Legal, user-authorized torrents only</span>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <TopBar
          connected={torrents.connected}
          refreshing={torrents.refreshing}
          onAdd={() => setAddOpen(true)}
          onRefresh={() =>
            torrents
              .refresh()
              .catch((err: Error) => torrents.setError(err.message))
          }
        />
        <main id="transfers" className="workspace">
          <div className="page-heading">
            <div>
              <h1>Transfers</h1>
              <p>Everything you're downloading, in one place.</p>
            </div>
            <span className="workspace-label">
              <HardDrive size={15} /> Local workspace
            </span>
          </div>
          <section
            className="transfer-summary"
            aria-label="Transfer overview"
            aria-busy={torrents.loading}
          >
            <div>
              <span>
                <ArrowDown size={16} /> Download speed
              </span>
              <strong>
                {formatSpeed(
                  torrents.allTasks.reduce(
                    (sum, task) => sum + task.download_speed,
                    0
                  )
                )}
              </strong>
            </div>
            <div>
              <span>
                <ArrowUp size={16} /> Upload speed
              </span>
              <strong>
                {formatSpeed(
                  torrents.allTasks.reduce(
                    (sum, task) => sum + task.upload_speed,
                    0
                  )
                )}
              </strong>
            </div>
            <div>
              <span>
                <Download size={16} /> Active downloads
              </span>
              <strong>
                {
                  torrents.allTasks.filter((task) =>
                    ['downloading', 'metadata'].includes(task.status)
                  ).length
                }
              </strong>
            </div>
            <div>
              <span>
                <HardDrive size={16} /> Downloaded
              </span>
              <strong>
                {formatBytes(
                  torrents.allTasks.reduce(
                    (sum, task) => sum + task.downloaded,
                    0
                  )
                )}
              </strong>
            </div>
          </section>
          <section className="task-pane">
            <div className="list-heading">
              <h2>
                {filters.find(
                  (filter) => filter.value === torrents.statusFilter
                )?.label ?? 'Transfers'}{' '}
                <span>{torrents.tasks.length}</span>
              </h2>
              <span>Select a transfer to view details</span>
            </div>
            <GlobalControls
              search={torrents.search}
              statusFilter={torrents.statusFilter}
              sort={torrents.sort}
              order={torrents.order}
              onSearch={torrents.setSearch}
              onStatusFilter={torrents.setStatusFilter}
              onSort={torrents.setSort}
              onOrder={torrents.setOrder}
            />
            {torrents.error && (
              <div className="error-banner" role="alert">
                {torrents.error}
              </div>
            )}
            <TaskTable
              tasks={torrents.tasks}
              loading={torrents.loading}
              failed={torrents.loadFailed}
              pendingActions={torrents.pendingActions}
              onClearFilters={() => {
                torrents.setSearch('');
                torrents.setStatusFilter('');
              }}
              selectedId={torrents.selectedId}
              onSelect={torrents.setSelectedId}
              onAdd={() => setAddOpen(true)}
              filtered={Boolean(torrents.search || torrents.statusFilter)}
              onAction={(id, action) =>
                torrents
                  .runAction(id, action)
                  .catch((err: Error) => torrents.setError(err.message))
              }
            />
          </section>
          {torrents.selectedTask && (
            <button
              className="drawer-backdrop"
              aria-label="Close transfer details"
              onClick={() => torrents.setSelectedId(null)}
            />
          )}
          <DetailDrawer
            key={torrents.selectedId}
            task={torrents.selectedTask}
            events={torrents.events}
            files={torrents.files}
            loading={torrents.detailsLoading}
            loadError={torrents.detailsError}
            pendingAction={
              torrents.selectedId
                ? torrents.pendingActions[torrents.selectedId]
                : undefined
            }
            onClose={() => torrents.setSelectedId(null)}
            onAction={torrents.runAction}
            onPatch={torrents.patchTask}
          />
        </main>
        <footer className="workspace-footer">
          <span>
            <span
              className={`connection-dot ${torrents.connected ? 'online' : ''}`}
            />{' '}
            {torrents.connected
              ? 'Connected  /  Updates in real time'
              : 'Reconnecting to live updates...'}
          </span>
          <span>Torrent Downloader / Local transfer manager</span>
        </footer>
      </div>
      <AddTorrentModal
        open={isAddOpen}
        onClose={() => setAddOpen(false)}
        onAddMagnet={(payload) =>
          torrents
            .addMagnetTask(payload)
            .then(() => setAddOpen(false))
            .catch((err: Error) => {
              torrents.setError(err.message);
              throw err;
            })
        }
        onAddFile={(payload) =>
          torrents
            .addFileTask(payload)
            .then(() => setAddOpen(false))
            .catch((err: Error) => {
              torrents.setError(err.message);
              throw err;
            })
        }
      />
    </div>
  );
}
