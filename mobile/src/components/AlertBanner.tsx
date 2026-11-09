import { Text, View } from 'react-native';

import { colors, radius, space } from '@/lib/theme';
import type { ServiceAlert } from '@/lib/types';
import { ALERT_LABEL, alertsForRoute, formatUntil, useAlerts } from '@/lib/useAlerts';

const TONE: Record<ServiceAlert['type'], { bg: string; fg: string }> = {
  no_service: { bg: '#FDECEA', fg: colors.danger },
  stop_moved: { bg: '#FFF4D6', fg: '#6B4E00' },
  delay: { bg: '#FFF4D6', fg: '#6B4E00' },
  announcement: { bg: '#E3EFE7', fg: colors.greenDark },
};

/** Shows active service alerts (optionally only those for one route) at the top of a screen. */
export function AlertBanner({ routeId, compact }: { routeId?: string | null; compact?: boolean }) {
  const { alerts } = useAlerts();
  const shown = alertsForRoute(alerts, routeId);
  if (!shown.length) return null;
  return (
    <View style={{ gap: space.xs }} accessibilityLiveRegion="polite">
      {shown.map((a) => (
        <View key={a.id} style={{ backgroundColor: TONE[a.type].bg, borderRadius: radius.sm, padding: space.sm, gap: 2 }}>
          <Text style={{ color: TONE[a.type].fg, fontWeight: '700' }}>
            {ALERT_LABEL[a.type]}: {a.title}
          </Text>
          {!compact && <Text style={{ color: colors.text }}>{a.message}</Text>}
          {!compact && a.ends_at && <Text style={{ color: colors.muted, fontSize: 12 }}>{formatUntil(a.ends_at)}</Text>}
        </View>
      ))}
    </View>
  );
}
