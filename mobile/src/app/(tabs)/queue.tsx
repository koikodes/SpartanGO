import { FlatList, Text, View } from 'react-native';

import { Button, Card, ErrorText, Screen, text } from '@/components/ui';
import { api } from '@/lib/api';
import { space } from '@/lib/theme';
import type { Ride, RideStatus } from '@/lib/types';
import { usePolling } from '@/lib/usePolling';
import { stopName, useRoutes } from '@/lib/useRoutes';

const NEXT: Partial<Record<RideStatus, { to: RideStatus; label: string }>> = {
  pending: { to: 'accepted', label: 'Accept' },
  accepted: { to: 'picked_up', label: 'Picked up' },
  picked_up: { to: 'completed', label: 'Drop off' },
};

export default function RideQueue() {
  const { routes } = useRoutes();
  const { data, error, refresh } = usePolling(() => api.rideQueue(), 8000);

  const advance = async (ride: Ride) => {
    const next = NEXT[ride.status];
    if (!next) return;
    await api.updateRide(ride.id, next.to);
    refresh();
  };

  return (
    <Screen>
      <ErrorText>{error}</ErrorText>
      <FlatList
        data={data ?? []}
        keyExtractor={(r) => String(r.id)}
        contentContainerStyle={{ gap: space.sm }}
        ListEmptyComponent={<Text style={[text.muted, { textAlign: 'center', marginTop: space.xl }]}>No ride requests right now.</Text>}
        renderItem={({ item }) => (
          <Card>
            <Text style={text.muted}>#{item.id} · {routes?.find((r) => r.id === item.route_id)?.name}</Text>
            <Text style={[text.body, { fontWeight: '600' }]}>
              {stopName(routes, item.route_id, item.pickup_stop_id)} → {stopName(routes, item.route_id, item.dropoff_stop_id)}
            </Text>
            {item.note ? <Text style={text.muted}>“{item.note}”</Text> : null}
            <View style={{ flexDirection: 'row', gap: space.sm }}>
              <View style={{ flex: 1 }}>
                {NEXT[item.status] && <Button title={NEXT[item.status]!.label} onPress={() => advance(item)} />}
              </View>
            </View>
          </Card>
        )}
      />
    </Screen>
  );
}
