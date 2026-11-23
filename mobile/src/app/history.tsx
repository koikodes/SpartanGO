import { Stack } from 'expo-router';
import { FlatList, Text, View } from 'react-native';

import { Card, ErrorText, text } from '@/components/ui';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { colors, space } from '@/lib/theme';
import type { Ride } from '@/lib/types';
import { usePolling } from '@/lib/usePolling';
import { stopName, useRoutes } from '@/lib/useRoutes';

const BADGE: Partial<Record<Ride['status'], { label: string; color: string }>> = {
  completed: { label: 'Dropped off', color: colors.success },
  cancelled: { label: 'Cancelled', color: colors.muted },
};

/** Finished rides (dropped off or cancelled). Students see their own; drivers and admins see everyone's. */
export default function RideHistory() {
  const { user } = useAuth();
  const { routes } = useRoutes();
  const { data, error } = usePolling(() => api.rideHistory(), 15000);
  const isStaff = user?.role === 'driver' || user?.role === 'admin';

  return (
    <>
      <Stack.Screen options={{ headerShown: true, title: 'Ride history', headerTintColor: colors.green }} />
      <View style={{ flex: 1, backgroundColor: colors.bg, padding: space.md }}>
        <ErrorText>{error}</ErrorText>
        <FlatList
          data={data ?? []}
          keyExtractor={(r) => String(r.id)}
          contentContainerStyle={{ gap: space.sm, paddingBottom: space.xl }}
          ListEmptyComponent={
            <Text style={[text.muted, { textAlign: 'center', marginTop: space.xl }]}>
              {data ? 'No past rides yet.' : 'Loading…'}
            </Text>
          }
          renderItem={({ item }) => {
            const badge = BADGE[item.status];
            return (
              <Card>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Text style={text.muted}>
                    {new Date(item.created_at).toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}
                    {isStaff ? ` · #${item.id}` : ''}
                  </Text>
                  {badge && <Text style={{ color: badge.color, fontWeight: '700' }}>{badge.label}</Text>}
                </View>
                <Text style={[text.body, { fontWeight: '600' }]}>
                  {stopName(routes, item.route_id, item.pickup_stop_id)} → {stopName(routes, item.route_id, item.dropoff_stop_id)}
                </Text>
                <Text style={text.muted}>{routes?.find((r) => r.id === item.route_id)?.name ?? item.route_id}</Text>
              </Card>
            );
          }}
        />
      </View>
    </>
  );
}
