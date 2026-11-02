import { useState } from 'react';
import {
  ArrowDown,
  ArrowUp,
  CheckCheck,
  Activity,
  ArrowDownToLine,
  HardDrive,
  Layers3,
  Pause,
  Search,
  ShieldCheck
} from 'lucide-react';
import { formatBytes, formatSpeed } from './utils/format';
import { AddTorrentModal } from './components/AddTorrentModal';
import { DetailDrawer } from './components/DetailDrawer';
import { GlobalControls } from './components/GlobalControls';
import { TaskTable } from './components/TaskTable';
import { TopBar } from './components/TopBar';
import { TorrentSearch } from './components/TorrentSearch';
import { useTorrents } from './state/useTorrents';

export function App() {
  const torrents = useTorrents();
  const [isAddOpen, setAddOpen] = useState(false);
  const [view, setView] = useState<'transfers' | 'search'>('transfers');

  const filters = [
    { value: '', label: 'All transfers', icon: Layers3 },
    { value: 'downloading', label: 'Downloading', icon: ArrowDown },
    { value: 'seeding', label: 'Seeding', icon: ArrowUp },
    { value: 'completed', label: 'Completed', icon: CheckCheck },
    { value: 'paused', label: 'Paused', icon: Pause }
  ];
  return (
    <div className="app-shell">
      <a className="skip-link" href="#workspace">
        Skip to content
      </a>
      <aside className="sidebar">
        <a className="brand-block" href="/" aria-label="Torrent Downloader home">
          <span className="brand-mark">
            <ArrowDownToLine size={21} strokeWidth={2.3} />
          </span>
          <span className="brand-wordmark">
            Torrent<span>Downloader</span>
          </span>
        </a>
        <div className="sidebar-workspace-label">PERSONAL WORKSPACE</div>
        <nav className="workspace-nav" aria-label="Workspace">
          <button
            className={`nav-item ${view === 'search' ? 'active' : ''}`}
            aria-current={view === 'search' ? 'page' : undefined}
            onClick={() => { setView('search'); torrents.setSelectedId(null); }}
          >
            <Search size={18} />
            <span>Find torrents</span>
          </button>
        </nav>
        <div className="nav-label">LIBRARY <span>{torrents.allTasks.length}</span></div>
        <nav aria-label="Transfer filters">
          {filters.map(({ value, label, icon: Icon }) => (
            <button
              key={value}
              aria-current={
                view === 'transfers' && torrents.statusFilter === value ? 'page' : undefined
              }
              className={`nav-item ${view === 'transfers' && torrents.statusFilter === value ? 'active' : ''}`}
              onClick={() => { setView('transfers'); torrents.setStatusFilter(value); }}
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
          <span className="sidebar-device-icon"><ShieldCheck size={17} /></span>
          <div>
            Running locally<span>Your transfers stay on this device</span>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <TopBar
          title={view === 'search' ? 'Find torrents' : 'Transfers'}
          connected={torrents.connected}
          refreshing={torrents.refreshing}
          onAdd={() => setAddOpen(true)}
          onRefresh={() =>
            torrents
              .refresh()
              .catch((err: Error) => torrents.setError(err.message))
          }
        />
        <main id="workspace" className="workspace">
          <div hidden={view !== 'search'}>
            <TorrentSearch
              onViewTransfers={() => setView('transfers')}
              onAdd={(magnet_uri) => torrents.addMagnetTask({
                magnet_uri, priority: 4, is_sequential: false
              })}
            />
          </div>
          <div hidden={view !== 'transfers'}>
          <div className="page-heading">
            <div>
              <div className="eyebrow"><span /> YOUR DOWNLOADS</div>
              <h1>Transfer center</h1>
              <p>A clear view of everything moving through your queue.</p>
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
            <div className="summary-card">
              <div className="summary-topline"><span>Download speed</span><span className="summary-icon down"><ArrowDown size={18} /></span></div>
              <strong>
                {formatSpeed(
                  torrents.allTasks.reduce(
                    (sum, task) => sum + task.download_speed,
                    0
                  )
                )}
              </strong>
              <small>Current incoming traffic</small>
            </div>
            <div className="summary-card">
              <div className="summary-topline"><span>Upload speed</span><span className="summary-icon up"><ArrowUp size={18} /></span></div>
              <strong>
                {formatSpeed(
                  torrents.allTasks.reduce(
                    (sum, task) => sum + task.upload_speed,
                    0
                  )
                )}
              </strong>
              <small>Current outgoing traffic</small>
            </div>
            <div className="summary-card">
              <div className="summary-topline"><span>Active transfers</span><span className="summary-icon active"><Activity size={18} /></span></div>
              <strong>
                {
                  torrents.allTasks.filter((task) =>
                    ['downloading', 'metadata'].includes(task.status)
                  ).length
                }
              </strong>
              <small>Downloading or connecting</small>
            </div>
            <div className="summary-card">
              <div className="summary-topline"><span>Data downloaded</span><span className="summary-icon storage"><HardDrive size={18} /></span></div>
              <strong>
                {formatBytes(
                  torrents.allTasks.reduce(
                    (sum, task) => sum + task.downloaded,
                    0
                  )
                )}
              </strong>
              <small>Across all transfers</small>
            </div>
          </section>
          <section className="task-pane">
            <div className="list-heading">
              <div>
                <div className="section-eyebrow">QUEUE MANAGEMENT</div>
                <h2>
                  {filters.find(
                    (filter) => filter.value === torrents.statusFilter
                  )?.label ?? 'Transfers'}{' '}
                  <span>{torrents.tasks.length}</span>
                </h2>
              </div>
              <span>Choose a transfer to inspect files and activity</span>
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
          </div>
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
