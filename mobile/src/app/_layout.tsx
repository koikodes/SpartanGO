import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

import { AuthProvider } from '@/lib/auth';
import { TrackerProvider } from '@/lib/tracker';

export default function RootLayout() {
  return (
    <AuthProvider>
      <TrackerProvider>
        <StatusBar style="dark" />
        <Stack screenOptions={{ headerShown: false }} />
      </TrackerProvider>
    </AuthProvider>
  );
}
