import { useEffect, useState } from 'react';
import { Alert, ScrollView, Text, View } from 'react-native';

import { Button, Card, Chip, ErrorText, Field, text } from '@/components/ui';
import { api } from '@/lib/api';
import { colors, space } from '@/lib/theme';
import type { Ride } from '@/lib/types';
import { usePolling } from '@/lib/usePolling';
import { stopName, useRoutes } from '@/lib/useRoutes';

const STATUS_LABEL: Record<Ride['status'], string> = {
  pending: 'Waiting for a driver',
  accepted: 'Driver is on the way',
  picked_up: 'On board',
  completed: 'Completed',
  cancelled: 'Cancelled',
};

export default function RequestRide() {
  const { routes } = useRoutes();
  const [routeId, setRouteId] = useState<string | null>(null);
  const [pickup, setPickup] = useState<string | null>(null);
  const [dropoff, setDropoff] = useState<string | null>(null);
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { data: rides, refresh } = usePolling(() => api.myRides(), 10000);

  useEffect(() => {
    if (!routeId && routes?.length) setRouteId(routes[0].id);
  }, [routes, routeId]);

  const route = routes?.find((r) => r.id === routeId);
  const open = rides?.find((r) => r.status === 'pending' || r.status === 'accepted' || r.status === 'picked_up');

  const submit = async () => {
    if (!route || !pickup || !dropoff) return;
    setBusy(true);
    setError(null);
    try {
      await api.requestRide({ route_id: route.id, pickup_stop_id: pickup, dropoff_stop_id: dropoff, note: note || undefined });
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
    return (
      <View style={{ flex: 1, backgroundColor: colors.bg, padding: space.md }}>
        <Card>
          <Text style={text.muted}>Your ride</Text>
          <Text style={text.h2}>{STATUS_LABEL[open.status]}</Text>
          <Text style={text.body}>
            {stopName(routes, open.route_id, open.pickup_stop_id)} → {stopName(routes, open.route_id, open.dropoff_stop_id)}
          </Text>
          {open.status !== 'picked_up' && <Button title="Cancel ride" variant="secondary" onPress={() => cancel(open)} />}
        </Card>
      </View>
    );
  }

  return (
    <ScrollView style={{ backgroundColor: colors.bg }} contentContainerStyle={{ padding: space.md, gap: space.md }}>
      <Text style={text.h2}>Route</Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>
        {(routes ?? []).map((r) => (
          <Chip key={r.id} label={r.name} color={r.color} selected={r.id === routeId}
            onPress={() => { setRouteId(r.id); setPickup(null); setDropoff(null); }} />
        ))}
      </View>

      <Text style={text.h2}>Pick up at</Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>
        {route?.stops.map((s) => <Chip key={s.id} label={s.name} selected={pickup === s.id} onPress={() => setPickup(s.id)} />)}
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
    </ScrollView>
  );
}
