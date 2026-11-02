// Each source publishes independently; cancellation also suppresses late callbacks.
export async function loadProviders<T>(
  providers: readonly string[],
  fetchProvider: (provider: string) => Promise<T>,
  onResult: (provider: string, result: T) => void,
  onError: (provider: string, error: Error) => void,
  signal: AbortSignal
): Promise<void> {
  await Promise.all(providers.map(async provider => {
    if (signal.aborted) return;
    try {
      const result = await fetchProvider(provider);
      if (!signal.aborted) onResult(provider, result);
    } catch (error) {
      if (!signal.aborted) onError(provider, error instanceof Error ? error : new Error('Search failed. Try again.'));
    }
  }));
}
