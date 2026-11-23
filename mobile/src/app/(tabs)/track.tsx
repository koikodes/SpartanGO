import { useKeepAwake } from 'expo-keep-awake';
import * as Location from 'expo-location';
import { useEffect, useRef, useState } from 'react';
import { ScrollView, Text, View } from 'react-native';

import { Button, Card, Chip, ErrorText, Field, Screen, text } from '@/components/ui';
import { api } from '@/lib/api';
import { colors, space } from '@/lib/theme';
import { useRoutes } from '@/lib/useRoutes';

const SEND_EVERY_MS = 5000; // matches how often the rider app polls /vehicles

/** Keeps the screen on while mounted. iOS stops foreground GPS when the screen locks. */
function StayAwake() {
  useKeepAwake('spartango-tracker');
  return null;
}

/**
 * Driver/admin view: turn this phone or tablet into the shuttle's GPS tracker.
 * Put the device on the shuttle, pick the route, tap Start, and leave this screen open.
 * Needs the backend running with TRACKER_PROVIDER=device.
 */
export default function TrackShuttle() {
  const { routes, error: routesError } = useRoutes();
  const [routeId, setRouteId] = useState<string | null>(null);
  const [vehicleId, setVehicleId] = useState('Shuttle 1');
  const [tracking, setTracking] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(0);
  // shown so the team can stand at a stop and copy its exact coordinates into routes.json
  const [position, setPosition] = useState<string | null>(null);

  const sub = useRef<Location.LocationSubscription | null>(null);
  const lastSent = useRef(0);
  const inFlight = useRef(false);

  useEffect(() => {
    if (!routeId && routes?.length) setRouteId(routes[0].id);
  }, [routes, routeId]);

  // stop the GPS watch if the screen is closed
  useEffect(() => () => sub.current?.remove(), []);

  const start = async () => {
    setError(null);
    if (!routeId) return setError('Pick the route this shuttle is running.');
    const name = vehicleId.trim();
    if (!name) return setError('Give this shuttle a name, e.g. "Shuttle 1".');

    const perm = await Location.requestForegroundPermissionsAsync();
    if (perm.status !== 'granted') {
      return setError('Location permission is off. Turn it on in Settings › Privacy & Security › Location Services.');
    }

    lastSent.current = 0;
    setSent(0);
    setTracking(true);
    setStatus('Waiting for GPS…');
    sub.current = await Location.watchPositionAsync(
      { accuracy: Location.Accuracy.BestForNavigation, timeInterval: SEND_EVERY_MS, distanceInterval: 0 },
      async ({ coords }) => {
        const now = Date.now();
        if (inFlight.current || now - lastSent.current < SEND_EVERY_MS - 500) return;
        inFlight.current = true;
        lastSent.current = now;
        try {
          await api.trackerPing({
            vehicle_id: name,
            route_id: routeId,
            lat: coords.latitude,
            lng: coords.longitude,
            heading: coords.heading != null && coords.heading >= 0 ? coords.heading : null,
            speed_mps: coords.speed != null && coords.speed >= 0 ? coords.speed : null,
            accuracy_m: coords.accuracy,
          });
          setSent((n) => n + 1);
          setError(null);
          setStatus(`Last sent ${new Date(now).toLocaleTimeString()} · accuracy ±${Math.round(coords.accuracy ?? 0)} m`);
          setPosition(`${coords.latitude.toFixed(5)}, ${coords.longitude.toFixed(5)}`);
        } catch (e) {
          setError(e instanceof Error ? e.message : 'Could not send location');
        } finally {
          inFlight.current = false;
        }
      },
      (reason) => setError(`GPS error: ${reason}`),
    );
  };

  const stop = async () => {
    sub.current?.remove();
    sub.current = null;
    setTracking(false);
    setStatus('Stopped. This shuttle is off the map.');
    try {
      await api.trackerStop(vehicleId.trim());
    } catch {
      // the backend drops it after 2 minutes anyway
    }
  };

  return (
    <Screen>
      {tracking && <StayAwake />}
      <ScrollView contentContainerStyle={{ gap: space.md }}>
        <Card>
          <Text style={text.h2}>Route</Text>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>
            {(routes ?? []).map((r) => (
              <Chip key={r.id} label={r.name} color={r.color} selected={routeId === r.id}
                onPress={() => !tracking && setRouteId(r.id)} />
            ))}
          </View>
          <Field label="Shuttle name" value={vehicleId} onChangeText={setVehicleId} editable={!tracking}
            autoCapitalize="words" placeholder="Shuttle 1" />
        </Card>

        {tracking
          ? <Button title="Stop tracking" variant="danger" onPress={stop} />
          : <Button title="Start tracking" onPress={start} disabled={!routes} />}

        <Card>
          <Text style={[text.body, { fontWeight: '700', color: tracking ? colors.success : colors.muted }]}>
            {tracking ? `● Live · ${sent} updates sent` : 'Not tracking'}
          </Text>
          {status && <Text style={text.muted}>{status}</Text>}
          {position && <Text selectable style={text.muted}>Position: {position}</Text>}
          <ErrorText>{error ?? routesError}</ErrorText>
        </Card>

        <Text style={text.muted}>
          Keep this screen open with the device plugged in. If the screen locks or you switch apps, updates stop and the
          shuttle leaves the map after 2 minutes.
        </Text>
      </ScrollView>
    </Screen>
  );
}
