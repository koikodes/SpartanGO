import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';

// MVP: local notifications fired by the app while it's open/backgrounded briefly.
// Next step (see README): server-side push via Expo push tokens so alerts arrive when the app is closed.

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldPlaySound: true,
    shouldSetBadge: false,
    shouldShowBanner: true,
    shouldShowList: true,
  }),
});

export async function ensureNotificationPermission(): Promise<boolean> {
  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('arrivals', {
      name: 'Shuttle arrivals',
      importance: Notifications.AndroidImportance.HIGH,
    });
  }
  const current = await Notifications.getPermissionsAsync();
  if (current.granted) return true;
  const { status } = await Notifications.requestPermissionsAsync();
  return status === 'granted';
}

export function notifyArrival(stopName: string, minutes: number) {
  return Notifications.scheduleNotificationAsync({
    content: {
      title: 'Your shuttle is close',
      body: minutes <= 1 ? `Arriving at ${stopName} now.` : `About ${minutes} min from ${stopName}.`,
    },
    trigger: null,
  });
}
