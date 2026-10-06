import { useEffect, useState } from 'react';

import { api } from './api';
import type { Route } from './types';

let cache: Route[] | null = null;

/** Routes and stops rarely change, so fetch once per app session. */
export function useRoutes() {
  const [routes, setRoutes] = useState<Route[] | null>(cache);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (cache) return;
    api.routes().then((r) => { cache = r; setRoutes(r); }).catch((e: Error) => setError(e.message));
  }, []);
  return { routes, error };
}

export function stopName(routes: Route[] | null, routeId: string, stopId: string) {
  return routes?.find((r) => r.id === routeId)?.stops.find((s) => s.id === stopId)?.name ?? stopId;
}
