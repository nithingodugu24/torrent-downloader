import { Plus, RefreshCcw, ChevronRight, FolderDown } from 'lucide-react';

interface TopBarProps {
  title: string;
  connected: boolean;
  refreshing: boolean;
  onAdd: () => void;
  onRefresh: () => void;
}

export function TopBar({
  title,
  connected,
  refreshing,
  onAdd,
  onRefresh
}: TopBarProps) {
  return (
    <header className="topbar">
      <div className="breadcrumb">
        <FolderDown size={17} />
        <span>Library</span>
        <ChevronRight size={14} />
        <strong>{title}</strong>
      </div>
      <div className="topbar-actions">
        <span className={`connection-pill ${connected ? 'online' : 'offline'}`}>
          <span className="connection-dot" />
          {connected ? 'Live connection' : 'Offline'}
        </span>
        <button
          className="icon-button"
          type="button"
          onClick={onRefresh}
          title="Refresh transfers"
          aria-label="Refresh transfers"
          disabled={refreshing}
        >
          <RefreshCcw
            className={refreshing ? 'spin' : ''}
            size={18}
            aria-hidden="true"
          />
        </button>
        <button className="primary-button" type="button" onClick={onAdd}>
          <Plus size={18} aria-hidden="true" />
          Add torrent
        </button>
      </div>
    </header>
  );
}
