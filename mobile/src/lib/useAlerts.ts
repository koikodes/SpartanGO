import { useEffect, useRef } from 'react';

import { api } from './api';
import { notifyLocal } from './notify';
import type { ServiceAlert } from './types';
import { usePolling } from './usePolling';

const seen = new Set<number>();
let primed = false;

/** Active service alerts, refreshed every 30 s. New alerts also pop a local notification
 *  (server push covers the app being closed). */
export function useAlerts() {
  const { data, error, refresh } = usePolling(() => api.alerts(), 30000);
  const first = useRef(true);

  useEffect(() => {
    if (!data) return;
    const fresh = data.filter((a) => !seen.has(a.id));
    fresh.forEach((a) => seen.add(a.id));
    // Don't replay every existing alert the first time the app loads.
    if (primed && !first.current) fresh.forEach((a) => notifyLocal(a.title, a.message));
    primed = true;
    first.current = false;
  }, [data]);

  return { alerts: data ?? [], error, refresh };
}

export function alertsForRoute(alerts: ServiceAlert[], routeId?: string | null) {
  return alerts.filter((a) => !routeId || a.route_ids.length === 0 || a.route_ids.includes(routeId));
}

export const ALERT_LABEL: Record<ServiceAlert['type'], string> = {
  stop_moved: 'Stop moved',
  no_service: 'No service',
  delay: 'Delay',
  announcement: 'Announcement',
};

export function formatUntil(iso: string | null) {
  if (!iso) return '';
  const d = new Date(iso);
  return `until ${d.toLocaleString([], { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}`;
}
