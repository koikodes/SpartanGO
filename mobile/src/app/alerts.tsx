import { Stack } from 'expo-router';
import { FlatList, Text } from 'react-native';

import { Card, ErrorText, Screen, text } from '@/components/ui';
import { api } from '@/lib/api';
import { colors, space } from '@/lib/theme';
import { ALERT_LABEL, formatUntil } from '@/lib/useAlerts';
import { usePolling } from '@/lib/usePolling';
import { useRoutes } from '@/lib/useRoutes';

/** Every rider can see current and upcoming service changes (moved stops, holidays, delays). */
export default function ServiceAlerts() {
  const { routes } = useRoutes();
  const { data, error } = usePolling(() => api.alerts(true), 30000);
  const routeNames = (ids: string[]) =>
    ids.length ? ids.map((id) => routes?.find((r) => r.id === id)?.name ?? id).join(', ') : 'All routes';

  return (
    <>
      <Stack.Screen options={{ headerShown: true, title: 'Service alerts', headerTintColor: colors.green }} />
      <Screen>
        <ErrorText>{error}</ErrorText>
        <FlatList
          data={data ?? []}
          keyExtractor={(a) => String(a.id)}
          contentContainerStyle={{ gap: space.sm }}
          ListEmptyComponent={<Text style={[text.muted, { textAlign: 'center', marginTop: space.xl }]}>No service changes right now.</Text>}
          renderItem={({ item }) => (
            <Card>
              <Text style={[text.muted, { fontWeight: '700', color: item.active ? colors.green : colors.muted }]}>
                {item.active ? 'Now' : `Starts ${new Date(item.starts_at).toLocaleString([], { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}`}
                {' · '}{ALERT_LABEL[item.type]} · {routeNames(item.route_ids)}
              </Text>
              <Text style={text.h2}>{item.title}</Text>
              <Text style={text.body}>{item.message}</Text>
              {item.moved_to_name && <Text style={text.body}>Temporary pickup: {item.moved_to_name}</Text>}
              {item.ends_at && <Text style={text.muted}>{formatUntil(item.ends_at)}</Text>}
            </Card>
          )}
        />
      </Screen>
    </>
  );
}
