import { useMemo, useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import MapView, { Marker, Polyline } from 'react-native-maps';

import { Chip, ErrorText, text } from '@/components/ui';
import { api } from '@/lib/api';
import { colors, space } from '@/lib/theme';
import { usePolling } from '@/lib/usePolling';
import { useRoutes } from '@/lib/useRoutes';

const NSU = { latitude: 36.8487, longitude: -76.2609, latitudeDelta: 0.02, longitudeDelta: 0.02 };

function loadLabel(load?: number | null) {
  if (load == null) return '';
  return load < 0.4 ? 'Seats available' : load < 0.8 ? 'Filling up' : 'Nearly full';
}

export default function LiveMap() {
  const { routes, error: routesError } = useRoutes();
  const [selected, setSelected] = useState<string | null>(null);
  const { data: vehicles, error } = usePolling(() => api.vehicles(), 5000);

  const shownRoutes = useMemo(() => (routes ?? []).filter((r) => !selected || r.id === selected), [routes, selected]);
  const colorFor = (routeId: string) => routes?.find((r) => r.id === routeId)?.color ?? colors.green;

  return (
    <View style={{ flex: 1 }}>
      <MapView style={StyleSheet.absoluteFill} initialRegion={NSU} showsUserLocation>
        {shownRoutes.map((r) => (
          <Polyline
            key={r.id}
            coordinates={[...r.stops, ...(r.is_loop ? [r.stops[0]] : [])].map((s) => ({ latitude: s.lat, longitude: s.lng }))}
            strokeColor={r.color}
            strokeWidth={4}
          />
        ))}
        {shownRoutes.flatMap((r) =>
          r.stops.map((s) => (
            <Marker key={`${r.id}-${s.id}`} coordinate={{ latitude: s.lat, longitude: s.lng }} title={s.name} description={r.name} pinColor={r.color} />
          )),
        )}
        {(vehicles ?? [])
          .filter((v) => !selected || v.route_id === selected)
          .map((v) => (
            <Marker key={v.id} coordinate={{ latitude: v.lat, longitude: v.lng }} title={`Shuttle ${v.id}`} description={loadLabel(v.passenger_load)}>
              <View style={[styles.bus, { backgroundColor: colorFor(v.route_id) }]}>
                <Text style={styles.busText}>🚌</Text>
              </View>
            </Marker>
          ))}
      </MapView>

      <View style={styles.overlay}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: space.sm }}>
          <Chip label="All routes" selected={!selected} onPress={() => setSelected(null)} />
          {(routes ?? []).map((r) => (
            <Chip key={r.id} label={r.name} color={r.color} selected={selected === r.id} onPress={() => setSelected(r.id)} />
          ))}
        </ScrollView>
        <ErrorText>{routesError ?? error}</ErrorText>
        {vehicles && <Text style={[text.muted, styles.count]}>{vehicles.length} shuttles running</Text>}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  overlay: { position: 'absolute', top: space.sm, left: space.sm, right: space.sm, gap: space.xs },
  bus: { padding: 6, borderRadius: 999, borderWidth: 2, borderColor: '#fff' },
  busText: { fontSize: 16 },
  count: { alignSelf: 'flex-start', backgroundColor: '#ffffffdd', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999 },
});
