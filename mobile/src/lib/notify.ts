import Constants from 'expo-constants';
import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';

import { api } from './api';

// Two kinds of notifications:
//  - Local: fired by the app itself while it's open (arrival alerts, ride status changes).
//  - Push: sent by the server through Expo when the app is closed (service alerts, ride assigned).
//    Needs a development/production build with an EAS project id; skipped quietly in Expo Go.

if (Platform.OS !== 'web') {
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldPlaySound: true,
      shouldSetBadge: false,
      shouldShowBanner: true,
      shouldShowList: true,
    }),
  });
}

export async function ensureNotificationPermission(): Promise<boolean> {
  if (Platform.OS === 'web') return false;
  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('arrivals', {
      name: 'Shuttle arrivals and service alerts',
      importance: Notifications.AndroidImportance.HIGH,
    });
  }
  const current = await Notifications.getPermissionsAsync();
  if (current.granted) return true;
  const { status } = await Notifications.requestPermissionsAsync();
  return status === 'granted';
}

export function notifyLocal(title: string, body: string) {
  if (Platform.OS === 'web') return Promise.resolve('');
  return Notifications.scheduleNotificationAsync({ content: { title, body }, trigger: null });
}

export function notifyArrival(stopName: string, minutes: number) {
  return notifyLocal('Your shuttle is close', minutes <= 1 ? `Arriving at ${stopName} now.` : `About ${minutes} min from ${stopName}.`);
}

/** Register this phone for server push (service alerts, ride assigned). Best effort. */
export async function registerForPush(): Promise<void> {
  try {
    if (Platform.OS === 'web' || !Device.isDevice) return;
    const projectId =
      (Constants.expoConfig?.extra as { eas?: { projectId?: string } } | undefined)?.eas?.projectId ??
      Constants.easConfig?.projectId;
    if (!projectId) return; // not set up for push yet (see mobile/README)
    if (!(await ensureNotificationPermission())) return;
    const { data } = await Notifications.getExpoPushTokenAsync({ projectId });
    await api.registerPushToken(data);
  } catch {
    // Push isn't available here (e.g. Expo Go on Android). In-app banners still work.
  }
}
