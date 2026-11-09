import * as Location from 'expo-location';
import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';

import { api } from './api';

/**
 * Tracker mode: the driver's phone (or a teammate riding the shuttle) shares its GPS position
 * so SpartanGO shows the real shuttle and real arrival times without access to NSU's Samsara.
 * Runs while the app is open on the Drive tab; the screen stays awake while tracking.
 */
interface TrackerState {
  vehicleId: string;
  routeId: string | null;
  tracking: boolean;
  lastSentAt: Date | null;
  error: string | null;
  setVehicleId: (v: string) => void;
  setRouteId: (r: string) => void;
  start: () => Promise<void>;
  stop: () => Promise<void>;
}

const TrackerContext = createContext<TrackerState | null>(null);
const SEND_EVERY_MS = 5000;

export function TrackerProvider({ children }: { children: ReactNode }) {
  const [vehicleId, setVehicleId] = useState('Shuttle 1');
  const [routeId, setRouteId] = useState<string | null>(null);
  const [tracking, setTracking] = useState(false);
  const [lastSentAt, setLastSentAt] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);
  const sub = useRef<Location.LocationSubscription | null>(null);
  const lastSend = useRef(0);
  const active = useRef<{ vehicleId: string; routeId: string } | null>(null);

  const stop = useCallback(async () => {
    sub.current?.remove();
    sub.current = null;
    const was = active.current;
    active.current = null;
    setTracking(false);
    if (was) {
      try { await api.trackerStop(was.vehicleId); } catch {}
    }
  }, []);

  const start = useCallback(async () => {
    setError(null);
    if (!routeId) { setError('Choose the route this shuttle is running.'); return; }
    if (!vehicleId.trim()) { setError('Enter the shuttle name, e.g. Shuttle 1.'); return; }
    const perm = await Location.requestForegroundPermissionsAsync();
    if (perm.status !== 'granted') { setError('Location access is needed to share the shuttle position.'); return; }
    await stop();
    active.current = { vehicleId: vehicleId.trim(), routeId };
    setTracking(true);
    sub.current = await Location.watchPositionAsync(
      { accuracy: Location.Accuracy.High, timeInterval: SEND_EVERY_MS, distanceInterval: 5 },
      async (pos) => {
        const now = Date.now();
        if (!active.current || now - lastSend.current < SEND_EVERY_MS - 500) return;
        lastSend.current = now;
        const { latitude, longitude, speed, heading } = pos.coords;
        try {
          await api.trackerPosition({
            vehicle_id: active.current.vehicleId,
            route_id: active.current.routeId,
            lat: latitude,
            lng: longitude,
            speed_mps: speed != null && speed >= 0 ? speed : null,
            heading: heading != null && heading >= 0 ? heading : null,
          });
          setLastSentAt(new Date());
          setError(null);
        } catch (e) {
          setError(e instanceof Error ? e.message : 'Could not send position');
        }
      },
    );
  }, [routeId, vehicleId, stop]);

  useEffect(() => () => { sub.current?.remove(); }, []);

  return (
    <TrackerContext.Provider value={{ vehicleId, routeId, tracking, lastSentAt, error, setVehicleId, setRouteId, start, stop }}>
      {children}
    </TrackerContext.Provider>
  );
}

export function useTracker() {
  const ctx = useContext(TrackerContext);
  if (!ctx) throw new Error('useTracker must be used inside TrackerProvider');
  return ctx;
}
