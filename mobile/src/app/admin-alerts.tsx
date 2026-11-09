import * as Location from 'expo-location';
import { Redirect, Stack } from 'expo-router';
import { useMemo, useState } from 'react';
import { Alert, ScrollView, Switch, Text, View } from 'react-native';

import { Button, Card, Chip, ErrorText, Field, text } from '@/components/ui';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { colors, space } from '@/lib/theme';
import type { AlertType } from '@/lib/types';
import { ALERT_LABEL, formatUntil } from '@/lib/useAlerts';
import { usePolling } from '@/lib/usePolling';
import { useRoutes } from '@/lib/useRoutes';

const TYPES: AlertType[] = ['stop_moved', 'no_service', 'delay', 'announcement'];

const STARTS = [
  { key: 'now', label: 'Now', at: () => null as Date | null },
  { key: 'tomorrow', label: 'Tomorrow 7 AM', at: () => { const d = new Date(); d.setDate(d.getDate() + 1); d.setHours(7, 0, 0, 0); return d; } },
];
const ENDS = [
  { key: '2h', label: 'In 2 hours', at: (s: Date) => new Date(s.getTime() + 2 * 3600e3) },
  { key: 'day', label: 'End of that day', at: (s: Date) => { const d = new Date(s); d.setHours(23, 59, 0, 0); return d; } },
  { key: '3d', label: '3 days', at: (s: Date) => new Date(s.getTime() + 3 * 86400e3) },
  { key: 'week', label: '1 week', at: (s: Date) => new Date(s.getTime() + 7 * 86400e3) },
  { key: 'none', label: 'Until I end it', at: () => null as Date | null },
];

/** Admin only: post a service alert. Every rider gets it as a banner and a push notification. */
export default function AdminAlerts() {
  const { user } = useAuth();
  const { routes } = useRoutes();
  const { data: alerts, refresh } = usePolling(() => api.allAlerts(), 30000);

  const [type, setType] = useState<AlertType>('stop_moved');
  const [title, setTitle] = useState('');
  const [message, setMessage] = useState('');
  const [routeIds, setRouteIds] = useState<string[]>([]);
  const [stopId, setStopId] = useState<string | null>(null);
  const [movedName, setMovedName] = useState('');
  const [movedAt, setMovedAt] = useState<{ lat: number; lng: number } | null>(null);
  const [startKey, setStartKey] = useState('now');
  const [endKey, setEndKey] = useState('day');
  const [notify, setNotify] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const stops = useMemo(() => {
    const rs = (routes ?? []).filter((r) => !routeIds.length || routeIds.includes(r.id));
    const seen = new Map<string, { id: string; name: string; lat: number; lng: number }>();
    rs.forEach((r) => r.stops.forEach((s) => seen.set(s.id, s)));
    return [...seen.values()];
  }, [routes, routeIds]);

  if (user && user.role !== 'admin') return <Redirect href="/more" />;

  const toggleRoute = (id: string) => setRouteIds((ids) => (ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]));

  const useHere = async () => {
    const perm = await Location.requestForegroundPermissionsAsync();
    if (perm.status !== 'granted') return setError('Location access is needed to use your current spot.');
    const pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High });
    setMovedAt({ lat: pos.coords.latitude, lng: pos.coords.longitude });
  };

  const submit = async () => {
    setError(null);
    const start = STARTS.find((s) => s.key === startKey)!.at();
    const end = ENDS.find((e) => e.key === endKey)!.at(start ?? new Date());
    setBusy(true);
    try {
      await api.createAlert({
        type, title: title.trim(), message: message.trim(), route_ids: routeIds,
        stop_id: type === 'stop_moved' ? stopId : null,
        moved_to_name: type === 'stop_moved' ? movedName.trim() : null,
        moved_to_lat: type === 'stop_moved' ? movedAt?.lat ?? null : null,
        moved_to_lng: type === 'stop_moved' ? movedAt?.lng ?? null : null,
        starts_at: start?.toISOString() ?? null,
        ends_at: end?.toISOString() ?? null,
        notify,
      });
      setTitle(''); setMessage(''); setStopId(null); setMovedName(''); setMovedAt(null);
      refresh();
      Alert.alert('Alert posted', notify ? 'Riders will see it in the app and get a notification.' : 'Riders will see it in the app.');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not post alert');
    } finally {
      setBusy(false);
    }
  };

  const end = (id: number) => Alert.alert('End this alert now?', undefined, [
    { text: 'Keep it' },
    { text: 'End now', style: 'destructive', onPress: async () => { await api.endAlert(id); refresh(); } },
  ]);

  const canPost = title.trim() && message.trim() && (type !== 'stop_moved' || (stopId && movedName.trim() && movedAt));
  const current = (alerts ?? []).filter((a) => a.active || new Date(a.starts_at) > new Date());

  return (
    <>
      <Stack.Screen options={{ headerShown: true, title: 'Post a service alert', headerTintColor: colors.green }} />
      <ScrollView style={{ backgroundColor: colors.bg }} contentContainerStyle={{ padding: space.md, gap: space.md, paddingBottom: space.xl }}>
        <Text style={text.h2}>What's happening?</Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>
          {TYPES.map((t) => <Chip key={t} label={ALERT_LABEL[t]} selected={type === t} onPress={() => setType(t)} />)}
        </View>

        <Text style={text.h2}>Which routes?</Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>
          <Chip label="All routes" selected={!routeIds.length} onPress={() => setRouteIds([])} />
          {(routes ?? []).map((r) => <Chip key={r.id} label={r.name} color={r.color} selected={routeIds.includes(r.id)} onPress={() => toggleRoute(r.id)} />)}
        </View>

        {type === 'stop_moved' && (
          <Card>
            <Text style={text.h2}>Which stop moved?</Text>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>
              {stops.map((s) => <Chip key={s.id} label={s.name} selected={stopId === s.id} onPress={() => setStopId(s.id)} />)}
            </View>
            <Field label="Temporary pickup spot" value={movedName} onChangeText={setMovedName} maxLength={80} placeholder="e.g. Front of the Student Center" />
            <Text style={text.muted}>Location of the temporary spot:</Text>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>
              {stops.filter((s) => s.id !== stopId).map((s) => (
                <Chip key={s.id} label={`At ${s.name}`} selected={movedAt?.lat === s.lat && movedAt?.lng === s.lng}
                  onPress={() => { setMovedAt({ lat: s.lat, lng: s.lng }); if (!movedName) setMovedName(s.name); }} />
              ))}
            </View>
            <Button title="Use where I'm standing" variant="secondary" onPress={useHere} />
            {movedAt && <Text style={text.muted}>Set to {movedAt.lat.toFixed(5)}, {movedAt.lng.toFixed(5)}</Text>}
          </Card>
        )}

        <Field label="Title (shown in the notification)" value={title} onChangeText={setTitle} maxLength={80}
          placeholder={type === 'no_service' ? 'No shuttles for Thanksgiving Break' : 'Library stop moved for tonight'} />
        <Field label="Message" value={message} onChangeText={setMessage} maxLength={500} multiline
          placeholder="What riders need to know and do" style={{ minHeight: 90, textAlignVertical: 'top' }} />

        <Text style={text.h2}>Starts</Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>
          {STARTS.map((s) => <Chip key={s.key} label={s.label} selected={startKey === s.key} onPress={() => setStartKey(s.key)} />)}
        </View>
        <Text style={text.h2}>Ends</Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>
          {ENDS.map((e) => <Chip key={e.key} label={e.label} selected={endKey === e.key} onPress={() => setEndKey(e.key)} />)}
        </View>

        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
          <Text style={text.body}>Send a push notification to riders</Text>
          <Switch value={notify} onValueChange={setNotify} trackColor={{ true: colors.green }} />
        </View>

        <ErrorText>{error}</ErrorText>
        <Button title="Post alert" onPress={submit} loading={busy} disabled={!canPost} />

        <Text style={[text.h2, { marginTop: space.md }]}>Current and upcoming</Text>
        {current.length === 0 && <Text style={text.muted}>No alerts right now.</Text>}
        {current.map((a) => (
          <Card key={a.id}>
            <Text style={text.muted}>{a.active ? 'Active' : 'Scheduled'} · {ALERT_LABEL[a.type]} {formatUntil(a.ends_at)}</Text>
            <Text style={[text.body, { fontWeight: '700' }]}>{a.title}</Text>
            <Text style={text.body}>{a.message}</Text>
            <Button title="End now" variant="secondary" onPress={() => end(a.id)} />
          </Card>
        ))}
      </ScrollView>
    </>
  );
}
