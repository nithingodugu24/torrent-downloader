import { useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import type { TaskEvent } from '../api/types';

export function LogPanel({
  events,
  loading
}: {
  events: TaskEvent[];
  loading: boolean;
}) {
  const [query, setQuery] = useState('');
  const filtered = useMemo(() => {
    const needle = query.toLowerCase();
    return events.filter(
      (event) =>
        event.message.toLowerCase().includes(needle) ||
        event.level.toLowerCase().includes(needle) ||
        event.event_type.toLowerCase().includes(needle)
    );
  }, [events, query]);

  return (
    <section className="log-panel">
      <div className="section-header">
        <h3>Activity</h3>
        <label className="mini-search">
          <Search size={14} aria-hidden="true" />
          <input
            aria-label="Search activity"
            placeholder="Search activity"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
      </div>
      {loading && (
        <p className="section-note" role="status">
          Loading activity...
        </p>
      )}
      {!loading && !filtered.length && (
        <p className="section-note">
          {query
            ? 'No activity matches your search.'
            : 'No activity recorded yet.'}
        </p>
      )}
      <div className="log-list">
        {filtered.map((event) => (
          <div className={`log-row ${event.level}`} key={event.id}>
            <time>{new Date(event.created_at).toLocaleTimeString()}</time>
            <strong>{event.event_type}</strong>
            <span>{event.message}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
