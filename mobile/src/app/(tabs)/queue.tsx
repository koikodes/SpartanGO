import { FlatList, Text, View } from 'react-native';

import { Button, Card, ErrorText, Screen, text } from '@/components/ui';
import { api } from '@/lib/api';
import { colors, formatEta, space } from '@/lib/theme';
import { useTracker } from '@/lib/tracker';
import type { Ride, RideStatus } from '@/lib/types';
import { usePolling } from '@/lib/usePolling';
import { findStop, pickupLabel, stopName, useRoutes } from '@/lib/useRoutes';

const NEXT: Partial<Record<RideStatus, { to: RideStatus; label: string }>> = {
  accepted: { to: 'picked_up', label: 'Picked up' },
  picked_up: { to: 'completed', label: 'Dropped off' },
};

/** Driver view. Riders are assigned to shuttles automatically; this shows the ones assigned
 *  to the shuttle in tracker mode, plus anyone still waiting for a shuttle. */
export default function RideQueue() {
  const { routes } = useRoutes();
  const tracker = useTracker();
  const myShuttle = tracker.tracking ? tracker.vehicleId : undefined;
  const { data, error, refresh } = usePolling(() => api.rideQueue(myShuttle), 5000, [myShuttle]);

  const advance = async (ride: Ride) => {
    if (ride.status === 'pending') await api.updateRide(ride.id, 'accepted', myShuttle);
    else {
      const next = NEXT[ride.status];
      if (!next) return;
      await api.updateRide(ride.id, next.to);
    }
    refresh();
  };

  const statusText = (r: Ride) => {
    if (r.status === 'pending') return 'Waiting for a shuttle';
    if (r.status === 'picked_up') return 'On board';
    return r.pickup_eta_seconds != null ? `Pick up in ${formatEta(r.pickup_eta_seconds)}` : 'Assigned';
  };

  return (
    <Screen>
      <Card style={{ backgroundColor: myShuttle ? '#E3EFE7' : colors.card }}>
        <Text style={text.body}>
          {myShuttle ? `Showing riders for ${myShuttle}` : 'Start tracker mode in the Drive tab to see riders assigned to your shuttle.'}
        </Text>
      </Card>
      <ErrorText>{error}</ErrorText>
      <FlatList
        data={data ?? []}
        keyExtractor={(r) => String(r.id)}
        contentContainerStyle={{ gap: space.sm }}
        ListEmptyComponent={<Text style={[text.muted, { textAlign: 'center', marginTop: space.xl }]}>No riders right now.</Text>}
        renderItem={({ item }) => (
          <Card>
            <Text style={text.muted}>
              {routes?.find((r) => r.id === item.route_id)?.name} · {statusText(item)}
              {item.vehicle_id && !myShuttle ? ` · ${item.vehicle_id}` : ''}
            </Text>
            <Text style={[text.body, { fontWeight: '600' }]}>
              {pickupLabel(findStop(routes, item.route_id, item.pickup_stop_id), item.pickup_stop_id)} → {stopName(routes, item.route_id, item.dropoff_stop_id)}
            </Text>
            {item.note ? <Text style={text.muted}>“{item.note}”</Text> : null}
            <View>
              {item.status === 'pending'
                ? myShuttle && <Button title="Take this rider" variant="secondary" onPress={() => advance(item)} />
                : NEXT[item.status] && <Button title={NEXT[item.status]!.label} onPress={() => advance(item)} />}
            </View>
          </Card>
        )}
      />
    </Screen>
  );
}
