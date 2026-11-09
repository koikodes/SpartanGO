import { useEffect, useState } from 'react';

import { api } from './api';
import type { Route, Stop } from './types';

// Routes rarely change, but service alerts can move a stop or pause a route,
// so refresh at most once a minute.
const MAX_AGE_MS = 60_000;
let cache: { at: number; data: Route[] } | null = null;
let inflight: Promise<Route[]> | null = null;

function load(): Promise<Route[]> {
  if (cache && Date.now() - cache.at < MAX_AGE_MS) return Promise.resolve(cache.data);
  if (!inflight) {
    inflight = api.routes()
      .then((r) => { cache = { at: Date.now(), data: r }; return r; })
      .finally(() => { inflight = null; });
  }
  return inflight;
}

export function useRoutes() {
  const [routes, setRoutes] = useState<Route[] | null>(cache?.data ?? null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    const run = () => load().then((r) => alive && setRoutes(r)).catch((e: Error) => alive && setError(e.message));
    run();
    const timer = setInterval(run, MAX_AGE_MS);
    return () => { alive = false; clearInterval(timer); };
  }, []);
  return { routes, error };
}

export function findStop(routes: Route[] | null, routeId: string, stopId: string): Stop | undefined {
  return routes?.find((r) => r.id === routeId)?.stops.find((s) => s.id === stopId);
}

export function stopName(routes: Route[] | null, routeId: string, stopId: string) {
  return findStop(routes, routeId, stopId)?.name ?? stopId;
}

/** Name to show for a pickup: the temporary location when a 'stop moved' alert is active. */
export function pickupLabel(stop: Stop | undefined, fallback: string) {
  if (!stop) return fallback;
  return stop.temporary ? `${stop.name} (moved to ${stop.temporary.name})` : stop.name;
}
