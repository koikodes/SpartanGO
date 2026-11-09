import { useKeepAwake } from 'expo-keep-awake';
import { useEffect } from 'react';
import { ScrollView, Text, View } from 'react-native';

import { Button, Card, Chip, ErrorText, Field, text } from '@/components/ui';
import { colors, space } from '@/lib/theme';
import { useTracker } from '@/lib/tracker';
import { useRoutes } from '@/lib/useRoutes';

function KeepAwake() {
  useKeepAwake();
  return null;
}

/** Driver tab: turn this phone into the shuttle's tracker so riders see the real shuttle. */
export default function Drive() {
  const { routes } = useRoutes();
  const t = useTracker();

  useEffect(() => {
    if (!t.routeId && routes?.length) t.setRouteId(routes[0].id);
  }, [routes, t]);

  return (
    <ScrollView style={{ backgroundColor: colors.bg }} contentContainerStyle={{ padding: space.md, gap: space.md }}>
      {t.tracking && <KeepAwake />}
      <Card style={{ backgroundColor: t.tracking ? '#E3EFE7' : colors.card }}>
        <Text style={text.h2}>{t.tracking ? `Sharing ${t.vehicleId}'s location` : 'Tracker mode is off'}</Text>
        <Text style={text.muted}>
          {t.tracking
            ? t.lastSentAt
              ? `Last update ${t.lastSentAt.toLocaleTimeString()}. Keep the app open on this screen.`
              : 'Waiting for GPS…'
            : 'Turn this on while riding the shuttle. Riders will see this shuttle live on the map, with arrival times.'}
        </Text>
      </Card>

      <Field label="Shuttle name" value={t.vehicleId} onChangeText={t.setVehicleId} editable={!t.tracking}
        placeholder="e.g. Shuttle 1" maxLength={40} autoCapitalize="words" />

      <Text style={text.h2}>Route this shuttle is running</Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>
        {(routes ?? []).map((r) => (
          <Chip key={r.id} label={r.name} color={r.color} selected={t.routeId === r.id}
            onPress={() => !t.tracking && t.setRouteId(r.id)} />
        ))}
      </View>

      <ErrorText>{t.error}</ErrorText>
      {t.tracking
        ? <Button title="Stop sharing location" variant="danger" onPress={t.stop} />
        : <Button title="Start tracker mode" onPress={t.start} />}

      <Text style={[text.muted, { lineHeight: 20 }]}>
        Only this shuttle's latest position is shared, every few seconds. It is never saved, and it
        disappears from the map as soon as you stop or after 2 minutes without an update. Ride
        requests assigned to this shuttle appear in the Queue tab.
      </Text>
    </ScrollView>
  );
}
