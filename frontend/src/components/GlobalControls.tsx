import { ArrowDownAZ, ArrowUpAZ, Search } from 'lucide-react';

interface GlobalControlsProps {
  search: string;
  statusFilter: string;
  sort: string;
  order: 'asc' | 'desc';
  onSearch: (value: string) => void;
  onStatusFilter: (value: string) => void;
  onSort: (value: string) => void;
  onOrder: (value: 'asc' | 'desc') => void;
}

export function GlobalControls({
  search,
  statusFilter,
  sort,
  order,
  onSearch,
  onStatusFilter,
  onSort,
  onOrder
}: GlobalControlsProps) {
  return (
    <div className="control-row">
      <label className="search-box">
        <Search size={17} aria-hidden="true" />
        <input
          value={search}
          onChange={(event) => onSearch(event.target.value)}
          placeholder="Search transfers..."
          aria-label="Search transfers"
        />
      </label>
      <select
        aria-label="Filter by status"
        value={statusFilter}
        onChange={(event) => onStatusFilter(event.target.value)}
      >
        <option value="">All statuses</option>
        <option value="queued">Queued</option>
        <option value="metadata">Metadata</option>
        <option value="downloading">Downloading</option>
        <option value="seeding">Seeding</option>
        <option value="paused">Paused</option>
        <option value="completed">Completed</option>
        <option value="errored">Errored</option>
        <option value="stopped">Stopped</option>
      </select>
      <select
        aria-label="Sort transfers"
        value={sort}
        onChange={(event) => onSort(event.target.value)}
      >
        <option value="created_at">Date added</option>
        <option value="name">Name</option>
        <option value="status">Status</option>
        <option value="progress">Progress</option>
        <option value="total_size">Size</option>
        <option value="ratio">Ratio</option>
      </select>
      <button
        className="icon-button"
        type="button"
        onClick={() => onOrder(order === 'asc' ? 'desc' : 'asc')}
        title={order === 'asc' ? 'Ascending' : 'Descending'}
      >
        {order === 'asc' ? (
          <ArrowUpAZ size={18} aria-hidden="true" />
        ) : (
          <ArrowDownAZ size={18} aria-hidden="true" />
        )}
      </button>
    </div>
  );
}
