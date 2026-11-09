import { useEffect, useRef, useState } from 'react';
import { Alert, ScrollView, StyleSheet, Text, View } from 'react-native';
import MapView, { Marker } from 'react-native-maps';

import { AlertBanner } from '@/components/AlertBanner';
import { Button, Card, Chip, ErrorText, Field, text } from '@/components/ui';
import { api } from '@/lib/api';
import { notifyLocal } from '@/lib/notify';
import { colors, formatEta, space } from '@/lib/theme';
import type { Ride } from '@/lib/types';
import { usePolling } from '@/lib/usePolling';
import { findStop, pickupLabel, stopName, useRoutes } from '@/lib/useRoutes';

const ARRIVING_SECONDS = 120;

function statusLine(r: Ride) {
  switch (r.status) {
    case 'pending': return 'Finding you a shuttle…';
    case 'accepted':
      return r.pickup_eta_seconds == null
        ? `${r.vehicle_id} is assigned to you`
        : r.pickup_eta_seconds < 45 ? `${r.vehicle_id} is arriving now` : `${r.vehicle_id} is on the way`;
    case 'picked_up': return 'On board';
    case 'completed': return 'Completed';
    case 'cancelled': return 'Cancelled';
  }
}

export default function RequestRide() {
  const { routes } = useRoutes();
  const [routeId, setRouteId] = useState<string | null>(null);
  const [pickup, setPickup] = useState<string | null>(null);
  const [dropoff, setDropoff] = useState<string | null>(null);
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { data: rides, refresh } = usePolling(() => api.myRides(), 5000);
  const lastStatus = useRef<Record<number, string>>({});
  const arrivingSent = useRef(new Set<number>());

  useEffect(() => {
    if (!routeId && routes?.length) setRouteId(routes[0].id);
  }, [routes, routeId]);

  const route = routes?.find((r) => r.id === routeId);
  const open = rides?.find((r) => r.status === 'pending' || r.status === 'accepted' || r.status === 'picked_up');

  // Ride updates as phone notifications (server push also covers the app being closed).
  useEffect(() => {
    if (!open) return;
    const before = lastStatus.current[open.id];
    const pickupName = stopName(routes, open.route_id, open.pickup_stop_id);
    if (before === 'pending' && open.status === 'accepted') {
      notifyLocal('Your shuttle is on the way', `${open.vehicle_id} is heading to ${pickupName}.`);
    }
    if (open.status === 'accepted' && open.pickup_eta_seconds != null && open.pickup_eta_seconds <= ARRIVING_SECONDS
        && !arrivingSent.current.has(open.id)) {
      arrivingSent.current.add(open.id);
      notifyLocal('Your shuttle is arriving', `${open.vehicle_id} is about ${Math.max(1, Math.round(open.pickup_eta_seconds / 60))} min from ${pickupName}.`);
    }
    lastStatus.current[open.id] = open.status;
  }, [open, routes]);

  const submit = async () => {
    if (!route || !pickup || !dropoff) return;
    setBusy(true);
    setError(null);
    try {
      const ride = await api.requestRide({ route_id: route.id, pickup_stop_id: pickup, dropoff_stop_id: dropoff, note: note || undefined });
      lastStatus.current[ride.id] = ride.status;
      setPickup(null);
      setDropoff(null);
      setNote('');
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not request ride');
    } finally {
      setBusy(false);
    }
  };

  const cancel = (ride: Ride) =>
    Alert.alert('Cancel ride?', undefined, [
      { text: 'Keep it' },
      { text: 'Cancel ride', style: 'destructive', onPress: async () => { await api.updateRide(ride.id, 'cancelled'); refresh(); } },
    ]);

  if (open) {
    const stop = findStop(routes, open.route_id, open.pickup_stop_id);
    const where = stop?.temporary ?? stop;
    const v = open.vehicle;
    return (
      <ScrollView style={{ backgroundColor: colors.bg }} contentContainerStyle={{ padding: space.md, gap: space.md }}>
        <AlertBanner routeId={open.route_id} />
        <Card>
          <Text style={text.muted}>Your ride</Text>
          <Text style={text.h2}>{statusLine(open)}</Text>
          {open.status === 'accepted' && open.pickup_eta_seconds != null && (
            <Text style={[text.h1, { color: colors.green }]}>
              {open.pickup_eta_seconds < 45 ? 'Arriving' : `about ${formatEta(open.pickup_eta_seconds)}`}
            </Text>
          )}
          <Text style={text.body}>
            {pickupLabel(stop, open.pickup_stop_id)} → {stopName(routes, open.route_id, open.dropoff_stop_id)}
          </Text>
          {open.status === 'accepted' && <Text style={text.muted}>Show your ride pass (or your NSU ID) when you board.</Text>}
        </Card>

        {where && (open.status === 'accepted' || open.status === 'pending') && (
          <View style={styles.mapBox}>
            <MapView
              style={StyleSheet.absoluteFill}
              region={{
                latitude: v ? (v.lat + where.lat) / 2 : where.lat,
                longitude: v ? (v.lng + where.lng) / 2 : where.lng,
                latitudeDelta: v ? Math.max(0.006, Math.abs(v.lat - where.lat) * 2.5) : 0.008,
                longitudeDelta: v ? Math.max(0.006, Math.abs(v.lng - where.lng) * 2.5) : 0.008,
              }}>
              <Marker coordinate={{ latitude: where.lat, longitude: where.lng }} title="Your pickup" pinColor={colors.green} />
              {v && (
                <Marker coordinate={{ latitude: v.lat, longitude: v.lng }} title={v.id}
                  description={v.source === 'simulated' ? 'Simulated shuttle' : 'Live location'}>
                  <View style={styles.bus}><Text style={{ fontSize: 16 }}>🚌</Text></View>
                </Marker>
              )}
            </MapView>
          </View>
        )}
        {open.status !== 'picked_up' && <Button title="Cancel ride" variant="secondary" onPress={() => cancel(open)} />}
      </ScrollView>
    );
  }

  const paused = route?.service_paused;
  return (
    <ScrollView style={{ backgroundColor: colors.bg }} contentContainerStyle={{ padding: space.md, gap: space.md }}>
      <AlertBanner routeId={routeId} />
      <Text style={text.h2}>Route</Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>
        {(routes ?? []).map((r) => (
          <Chip key={r.id} label={r.name} color={r.color} selected={r.id === routeId}
            onPress={() => { setRouteId(r.id); setPickup(null); setDropoff(null); }} />
        ))}
      </View>

      {paused ? (
        <Card><Text style={text.body}>No rides available on this route right now: {paused}.</Text></Card>
      ) : (
        <>
          <Text style={text.h2}>Pick up at</Text>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>
            {route?.stops.map((s) => (
              <Chip key={s.id} label={s.temporary ? `${s.name} → ${s.temporary.name}` : s.name}
                selected={pickup === s.id} onPress={() => setPickup(s.id)} />
            ))}
          </View>

          <Text style={text.h2}>Drop off at</Text>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>
            {route?.stops.filter((s) => s.id !== pickup).map((s) => (
              <Chip key={s.id} label={s.name} selected={dropoff === s.id} onPress={() => setDropoff(s.id)} />
            ))}
          </View>

          <Field label="Note for driver (optional)" value={note} onChangeText={setNote} maxLength={200} placeholder="e.g. wheelchair access needed" />
          <ErrorText>{error}</ErrorText>
          <Button title="Request ride" onPress={submit} loading={busy} disabled={!pickup || !dropoff} />
          <Text style={[text.muted, { textAlign: 'center' }]}>We'll assign the closest shuttle with room. No need to pick a driver.</Text>
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  mapBox: { height: 240, borderRadius: 12, overflow: 'hidden', borderWidth: 1, borderColor: colors.border },
  bus: { padding: 6, borderRadius: 999, borderWidth: 2, borderColor: '#fff', backgroundColor: colors.gold },
});
