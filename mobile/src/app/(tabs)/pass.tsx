import { useEffect, useState } from 'react';
import { Text, View } from 'react-native';
import QRCode from 'react-native-qrcode-svg';

import { Card, ErrorText, Screen, text } from '@/components/ui';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { colors, space } from '@/lib/theme';
import type { Pass } from '@/lib/types';

/** Rotating QR pass. The code changes every ~30s, so a screenshot can't be shared to ride free. */
export default function RidePass() {
  const { user } = useAuth();
  const [pass, setPass] = useState<Pass | null>(null);
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let refreshTimer: ReturnType<typeof setTimeout>;
    let cancelled = false;
    const load = async () => {
      try {
        const p = await api.pass();
        if (cancelled) return;
        setPass(p);
        setSecondsLeft(p.expires_in);
        setError(null);
        refreshTimer = setTimeout(load, Math.max(1, p.expires_in) * 1000);
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : 'Could not load pass');
        refreshTimer = setTimeout(load, 5000);
      }
    };
    load();
    const tick = setInterval(() => setSecondsLeft((s) => Math.max(0, s - 1)), 1000);
    return () => { cancelled = true; clearTimeout(refreshTimer); clearInterval(tick); };
  }, []);

  return (
    <Screen style={{ alignItems: 'center', justifyContent: 'center' }}>
      <Card style={{ alignItems: 'center', padding: space.lg, gap: space.md, width: '100%' }}>
        <Text style={[text.h2, { color: colors.green }]}>Prototype Ride Pass</Text>
        <Text style={text.muted}>Capstone demo · not an official NSU ID</Text>
        <Text style={text.body}>{user?.name}</Text>
        <View style={{ padding: space.md, backgroundColor: '#fff', borderRadius: 12 }}>
          {pass ? <QRCode value={pass.token} size={240} color={colors.text} /> : <View style={{ width: 240, height: 240 }} />}
        </View>
        <Text style={text.muted}>Refreshes in {secondsLeft}s · show this to your driver</Text>
        <ErrorText>{error}</ErrorText>
      </Card>
    </Screen>
  );
}
