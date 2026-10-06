import { useCallback, useEffect, useRef, useState } from 'react';
import { AppState } from 'react-native';

/** Fetch now, then every `intervalMs` while the app is in the foreground. */
export function usePolling<T>(fetcher: () => Promise<T>, intervalMs: number, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const refresh = useCallback(async () => {
    try {
      setData(await fetcherRef.current());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong');
    }
  }, []);

  useEffect(() => {
    let timer: ReturnType<typeof setInterval> | null = null;
    const start = () => {
      refresh();
      timer = setInterval(refresh, intervalMs);
    };
    const stop = () => {
      if (timer) clearInterval(timer);
      timer = null;
    };
    start();
    const sub = AppState.addEventListener('change', (s) => (s === 'active' ? (stop(), start()) : stop()));
    return () => {
      stop();
      sub.remove();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs, refresh, ...deps]);

  return { data, error, refresh };
}
