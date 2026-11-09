import { useEffect, useRef, useState } from 'react';
import { FlatList, Pressable, ScrollView, Text, View } from 'react-native';

import { AlertBanner } from '@/components/AlertBanner';
import { Icon } from '@/components/Icon';
import { Card, Chip, ErrorText, Screen, text } from '@/components/ui';
import { api } from '@/lib/api';
import { ensureNotificationPermission, notifyArrival } from '@/lib/notify';
import { colors, formatEta, space } from '@/lib/theme';
import type { Arrival, ArrivalKind } from '@/lib/types';
import { usePolling } from '@/lib/usePolling';
import { useRoutes } from '@/lib/useRoutes';

const ALERT_SECONDS = 180; // notify when the shuttle is ~3 minutes out

const KIND_LABEL: Record<ArrivalKind, string> = { live: 'Live', simulated: 'Simulated', scheduled: 'Scheduled' };

/** e.g. "Live · about 4 min, 12 min". Always says where the time came from. */
function describe(list: Arrival[]) {
  const kind = list[0].kind;
  return `${KIND_LABEL[kind]} · ${list.map((a, i) => (i === 0 && a.eta_seconds >= 45 ? `about ${formatEta(a.eta_seconds)}` : formatEta(a.eta_seconds))).join(', ')}`;
}

export default function Arrivals() {
  const { routes, error: routesError } = useRoutes();
  const [routeId, setRouteId] = useState<string | null>(null);
  const [watched, setWatched] = useState<string | null>(null); // stop id with alerts on
  const alerted = useRef(new Set<string>());

  useEffect(() => {
    if (!routeId && routes?.length) setRouteId(routes[0].id);
  }, [routes, routeId]);

  const route = routes?.find((r) => r.id === routeId);

  const { data, error } = usePolling(
    async () => {
      if (!route) return {} as Record<string, Arrival[]>;
      const lists = await Promise.all(route.stops.map((s) => api.arrivals(route.id, s.id)));
      return Object.fromEntries(route.stops.map((s, i) => [s.id, lists[i]]));
    },
    15000,
    [route?.id],
  );

  // Fire one notification per approaching shuttle for the watched stop.
  useEffect(() => {
    if (!watched || !data || !route) return;
    const next = data[watched]?.[0];
    if (next && next.eta_seconds <= ALERT_SECONDS) {
      const key = `${watched}:${next.vehicle_id ?? 'scheduled'}`;
      if (!alerted.current.has(key)) {
        alerted.current.add(key);
        const stop = route.stops.find((s) => s.id === watched);
        notifyArrival(stop?.name ?? 'your stop', Math.round(next.eta_seconds / 60));
      }
    } else if (next) {
      // shuttle moved on / new one coming: allow alerting again
      for (const k of alerted.current) if (k.startsWith(`${watched}:`) && k !== `${watched}:${next.vehicle_id ?? 'scheduled'}`) alerted.current.delete(k);
    }
  }, [data, watched, route]);

  const toggleWatch = async (stopId: string) => {
    if (watched === stopId) return setWatched(null);
    if (await ensureNotificationPermission()) setWatched(stopId);
  };

  return (
    <Screen>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: space.sm }} style={{ flexGrow: 0 }}>
        {(routes ?? []).map((r) => (
          <Chip key={r.id} label={r.name} color={r.color} selected={r.id === routeId} onPress={() => setRouteId(r.id)} />
        ))}
      </ScrollView>
      <AlertBanner routeId={routeId} />
      <ErrorText>{routesError ?? error}</ErrorText>
      <FlatList
        data={route?.stops ?? []}
        keyExtractor={(s) => s.id}
        contentContainerStyle={{ gap: space.sm, paddingBottom: space.lg }}
        renderItem={({ item }) => {
          const list = data?.[item.id] ?? [];
          const on = watched === item.id;
          return (
            <Card style={{ flexDirection: 'row', alignItems: 'center' }}>
              <View style={{ flex: 1, gap: 2 }}>
                <Text style={[text.body, { fontWeight: '600' }]}>{item.name}</Text>
                {item.temporary && <Text style={{ color: '#6B4E00' }}>Moved to {item.temporary.name} for now</Text>}
                <Text style={text.muted}>
                  {route?.service_paused
                    ? `No service: ${route.service_paused}`
                    : data == null ? 'Loading…' : list.length ? describe(list) : 'No shuttle approaching'}
                </Text>
              </View>
              <Pressable
                onPress={() => toggleWatch(item.id)}
                accessibilityRole="button"
                accessibilityLabel={on ? `Stop alerts for ${item.name}` : `Alert me for ${item.name}`}
                hitSlop={12}>
                <Icon name={on ? 'bell' : 'bellOff'} color={on ? colors.gold : colors.muted} />
              </Pressable>
            </Card>
          );
        }}
      />
      {watched && <Text style={[text.muted, { textAlign: 'center' }]}>We'll notify you when a shuttle is about 3 minutes away.</Text>}
    </Screen>
  );
}
