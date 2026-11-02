import { useEffect, useRef, useState } from 'react';
import { ArrowRight, Check, Clock3, Download, ExternalLink, Search, Info } from 'lucide-react';
import { loadProviders } from '../utils/loadProviders';
import { AvailabilitySignal } from './AvailabilitySignal';
import { estimateSearchTime } from '../utils/downloadEstimate';
import { estimateAvailability } from '../utils/availability';
import { searchTorrents, resolveSearchMagnet, type SearchResult, type SearchResponse } from '../api/client';

const providers = { bitsearch: 'Bitsearch', uindex: 'UIndex', limetorrents: 'LimeTorrents', piratebay: 'The Pirate Bay', torrentdownload: 'TorrentDownload' };

export function TorrentSearch({ onAdd, onViewTransfers }: { onAdd: (magnet: string) => Promise<unknown>; onViewTransfers: () => void }) {
  const [query, setQuery] = useState('');
  const [provider, setProvider] = useState('all');
  const [sort, setSort] = useState('availability');
  const [estimateMbps, setEstimateMbps] = useState('');
  const [notice, setNotice] = useState('');
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [sourceStates, setSourceStates] = useState<Record<string, 'loading' | 'done' | 'error'>>({});
  const [error, setError] = useState('');
  const [pending, setPending] = useState<string | null>(null);
  const [added, setAdded] = useState<Set<string>>(new Set());
  const [lastSearch, setLastSearch] = useState({ query: '', provider: 'all' });
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);

  async function run(page: number, fresh = false) {
    const criteria = fresh ? { query: query.trim(), provider } : lastSearch;
    controller.current?.abort();
    const next = new AbortController();
    controller.current = next;
    const selected = criteria.provider === 'all' ? Object.keys(providers) : [criteria.provider];
    setBusy(true); setError(''); setNotice('');
    setResponse({ results: [], errors: {}, page });
    setSourceStates(Object.fromEntries(selected.map(key => [key, 'loading'])));
    setLastSearch(criteria);
    try {
      await loadProviders(
        selected,
        source => searchTorrents(criteria.query, source, page, next.signal),
        (source, result) => {
          setResponse(previous => previous && ({
            ...previous,
            results: [...previous.results, ...result.results.filter(item => !previous.results.some(existing => existing.url === item.url))],
            errors: { ...previous.errors, ...result.errors }
          }));
          setSourceStates(previous => ({ ...previous, [source]: result.errors[source] ? 'error' : 'done' }));
        },
        (source, failure) => {
          setResponse(previous => previous && ({ ...previous, errors: { ...previous.errors, [source]: failure.message } }));
          setSourceStates(previous => ({ ...previous, [source]: 'error' }));
        },
        next.signal
      );
    } finally {
      if (!next.signal.aborted) setBusy(false);
    }
  }

  function stopSearch() {
    controller.current?.abort();
    setBusy(false);
  }

  async function add(result: SearchResult) {
    if (pending) return;
    setPending(result.url); setError('');
    try {
      const magnet = result.magnet_uri ?? await resolveSearchMagnet(result);
      await onAdd(magnet);
      setAdded(previous => new Set(previous).add(result.url));
      setNotice(`Added “${result.title}” to your transfers.`);
    } catch (err) { setError((err as Error).message); }
    finally { setPending(null); }
  }

  const results = [...(response?.results ?? [])].sort((a, b) => {
    if (sort === 'source') return Object.keys(providers).indexOf(a.provider) - Object.keys(providers).indexOf(b.provider);
    const difference = estimateAvailability(b.seeds, b.leeches).rank - estimateAvailability(a.seeds, a.leeches).rank;
    return difference || (b.seeds ?? -1) - (a.seeds ?? -1);
  });
  const stopped = !busy && Object.values(sourceStates).includes('loading');

  return <section className="torrent-search" aria-labelledby="torrent-search-title">
    <div className="page-heading search-page-heading">
      <div><h1 id="torrent-search-title">Find your next download</h1>
        <p>Search {Object.keys(providers).length} sources. Pick a torrent that’s more likely to keep moving.</p></div>
      <button className="ghost-button back-to-transfers" onClick={onViewTransfers}>Your transfers <ArrowRight size={16} /></button>
    </div>
    <div className="search-surface">
      <form className="torrent-search-form" onSubmit={event => { event.preventDefault(); void run(1, true); }}>
        <label className="field search-query">What are you looking for?
          <span className="search-input-wrap"><Search size={20} aria-hidden="true" />
            <input value={query} maxLength={200} required placeholder="Search by name or keywords" onChange={event => setQuery(event.target.value)} />
          </span>
        </label>
        <label className="field">Search in
          <select value={provider} onChange={event => setProvider(event.target.value)}>
            <option value="all">All sources</option>
            {Object.entries(providers).map(([key, name]) => <option key={key} value={key}>{name}</option>)}
          </select>
        </label>
        <button className="primary-button" disabled={!query.trim()}>{busy ? 'Search again' : 'Find torrents'}<ArrowRight size={17} aria-hidden="true" /></button>
      </form>
      <div className="search-speed-estimator">
        <label htmlFor="estimate-speed">Your internet speed <span>(optional)</span></label>
        <div><input id="estimate-speed" type="number" min="0.1" max="100000" step="0.1" inputMode="decimal" placeholder="e.g. 100" value={estimateMbps} onChange={event => setEstimateMbps(event.target.value)} aria-describedby="estimate-speed-help" /><span>Mbps</span></div>
        <p id="estimate-speed-help">Enter your speed for a rough download-time estimate. Actual torrent speed can be lower.</p>
      </div>
      <details className="availability-guide">
        <summary><Info size={15} aria-hidden="true" />How do I choose a download?</summary>
        <div><p>Start with <strong>Well shared</strong> or <strong>Available</strong>. These have more people reported to hold the complete file.</p>
          <p><strong>May be slow</strong> means very few complete copies, or many people downloading per copy. <strong>May not finish</strong> means no complete copies were reported. Missing counts show as <strong>Availability unknown</strong>.</p>
          <p>These are estimates from the search site, not a connection test. Counts can be outdated. Your connection and other people’s upload speeds affect actual speed; completion is never guaranteed.</p>
        <p>Signal bars summarize availability: four means many complete copies, three means several, two means heavy demand, one means very few copies, and empty bars mean none reported. Unknown counts are shown separately. This is not a measured probability.</p></div>
      </details>
    </div>
    {error && <div className="error-banner" role="alert">{error}</div>}
    {notice && <div className="search-added-notice" role="status"><Check size={17} /><span>{notice}</span><button className="ghost-button" onClick={onViewTransfers}>View transfers <ArrowRight size={15} /></button></div>}
    <div className="search-results-toolbar">
      <p role="status">{response ? `${response.results.length} results for “${lastSearch.query}”${busy ? ' · more sources loading…' : stopped ? ' · search stopped' : ''}` : Object.values(providers).join(' · ')}</p>
      {!!response?.results.length && <label>Sort by <select aria-label="Sort search results" value={sort} onChange={event => setSort(event.target.value)}><option value="availability">Best availability</option><option value="source">Source order</option></select></label>}
      {busy && <button className="ghost-button" type="button" onClick={stopSearch}>Stop search</button>}
    </div>
    {response && <ul className="source-progress" aria-label="Search source progress">
      {Object.entries(sourceStates).map(([key, state]) => <li key={key} className={`source-${state}`}>
        <span>{providers[key as keyof typeof providers]}</span>
        <span>{state === 'loading' ? busy ? 'Searching…' : 'Stopped' : state === 'error' ? 'Unavailable' : `${response.results.filter(item => item.provider === key).length} results`}</span>
      </li>)}
    </ul>}
    {response && Object.entries(response.errors).map(([key, message]) => <p className="search-warning" key={key} role="status"><strong>{providers[key as keyof typeof providers]}:</strong> {message}</p>)}
    {!response && !busy && !error && <div className="search-empty"><Search size={30} strokeWidth={1.5} aria-hidden="true" /><h2>A good download starts with a good source</h2><p>Search above, then look for the availability label beside each result. No torrent jargon needed.</p></div>}
    {busy && !results.length && <div className="search-loading" aria-hidden="true">{[0, 1, 2].map(index => <div key={index}><span /><span /></div>)}</div>}
    {response && !busy && !results.length && <div className="search-empty"><Search size={28} aria-hidden="true" /><h2>{stopped ? 'Search stopped' : Object.keys(response.errors).length ? 'No results available' : 'No matching torrents'}</h2><p>{stopped ? 'Search again to check the remaining sources.' : Object.keys(response.errors).length ? 'Retry your search or choose another source.' : 'Try fewer words or a different name.'}</p></div>}
    {!!results.length && <>
      <div className="search-column-head" aria-hidden="true"><span>Torrent</span><span>Estimated availability</span><span /></div>
      <ul className="search-result-list" aria-label="Torrent search results">
        {results.map(result => {
          const outlook = estimateAvailability(result.seeds, result.leeches);
          const isAdded = added.has(result.url);
          return <li className="search-result" key={result.url}>
            <div className="search-result-info"><a className="search-result-title" href={result.url} target="_blank" rel="noopener noreferrer">{result.title}<ExternalLink size={13} aria-hidden="true" /></a>
              <div className="search-result-meta"><span>{providers[result.provider]}</span><span>{result.size ?? 'Size unknown'}</span></div>
            </div>
            <div className={`result-outlook outlook-${outlook.tone}`}>
              <strong><AvailabilitySignal bars={outlook.bars} />{outlook.label}</strong><p>{outlook.description}</p>
              <div className="search-time-estimate"><Clock3 size={13} aria-hidden="true" /><span>{estimateSearchTime(result.size, Number(estimateMbps))}<small>{Number(estimateMbps) > 0 ? `At ${estimateMbps} Mbps · may take longer` : 'Add your internet speed above to estimate'}</small></span></div>
              <details className="result-counts"><summary>Source counts</summary><p>{result.seeds?.toLocaleString() ?? 'Unknown'} complete copies (seeds)<br />{result.leeches?.toLocaleString() ?? 'Unknown'} downloading (peers)</p></details>
            </div>
            <button className={isAdded ? 'ghost-button result-download added' : 'primary-button result-download'} aria-label={`${isAdded ? 'Added' : 'Download'} ${result.title}`} disabled={!!pending || isAdded} onClick={() => void add(result)}>
              {isAdded ? <Check size={16} aria-hidden="true" /> : <Download size={16} aria-hidden="true" />}{isAdded ? 'Added' : pending === result.url ? 'Adding…' : 'Download'}
            </button>
          </li>;
        })}
      </ul>
      <p className="availability-footnote">Availability is estimated from source counts. Actual speed and completion depend on the people you can connect to.</p>
    </>}
    {response && <div className="search-pagination"><button className="ghost-button" disabled={busy || response.page <= 1} onClick={() => void run(response.page - 1)}>Previous</button><span>Page {response.page}</span><button className="ghost-button" disabled={busy || !results.length || response.page >= 100} onClick={() => void run(response.page + 1)}>Next page</button></div>}
  </section>;
}
