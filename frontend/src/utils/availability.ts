export interface Availability {
  label: string;
  description: string;
  tone: 'good' | 'fair' | 'slow' | 'poor' | 'unknown';
  rank: number;
}

// A conservative reading of index-reported counts, not a measured speed or probability.
// The 5/20-copy bands and 10 downloaders per copy are UI heuristics, not protocol limits.
export function estimateAvailability(seeds: number | null, leeches: number | null): Availability {
  if (seeds === null || !Number.isFinite(seeds) || seeds < 0) {
    return { label: 'Availability unknown', description: 'This source has no complete-copy count.', tone: 'unknown', rank: 1 };
  }
  if (seeds === 0) {
    return { label: 'May not finish', description: 'No complete copies reported. You may need to wait.', tone: 'poor', rank: 0 };
  }
  if (seeds < 5) {
    return { label: 'May be slow', description: 'Very few complete copies. Progress may be slow or stop.', tone: 'slow', rank: 2 };
  }
  if (leeches !== null && leeches > seeds * 10) {
    return { label: 'Busy · may be slow', description: 'Many people downloading for each complete copy.', tone: 'slow', rank: 3 };
  }
  if (seeds < 20) {
    return { label: 'Available', description: 'Several complete copies reported. A reasonable option to try.', tone: 'fair', rank: 4 };
  }
  return { label: 'Well shared', description: 'Many complete copies reported. A better chance of steady progress.', tone: 'good', rank: 5 };
}
