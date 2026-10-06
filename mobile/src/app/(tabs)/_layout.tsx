import { Redirect } from 'expo-router';
import { Tabs } from 'expo-router/js-tabs';
import { ActivityIndicator, Pressable, Text, View, type ColorValue } from 'react-native';

import { Icon, type IconName } from '@/components/Icon';
import { useAuth } from '@/lib/auth';
import { colors } from '@/lib/theme';

export default function TabsLayout() {
  const { user, loading, signOut } = useAuth();

  if (loading) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.bg }}>
        <ActivityIndicator color={colors.green} size="large" />
      </View>
    );
  }
  if (!user) return <Redirect href="/login" />;

  const isStaff = user.role === 'driver' || user.role === 'admin';
  const icon = (name: IconName) => ({ color }: { color: ColorValue }) => <Icon name={name} color={color} />;
  // Students see Map / Arrivals / Ride / Pass. Drivers see Map / Queue / Scan.
  const studentOnly = isStaff ? { href: null } : {};
  const staffOnly = isStaff ? {} : { href: null };

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: colors.green,
        tabBarInactiveTintColor: colors.muted,
        headerTintColor: colors.text,
        headerRight: () => (
          <Pressable onPress={signOut} style={{ paddingHorizontal: 16 }} accessibilityRole="button">
            <Text style={{ color: colors.green, fontWeight: '600' }}>Sign out</Text>
          </Pressable>
        ),
      }}>
      <Tabs.Screen name="index" options={{ title: 'Live map', tabBarLabel: 'Map', tabBarIcon: icon('map') }} />
      <Tabs.Screen name="arrivals" options={{ title: 'Arrivals', tabBarIcon: icon('clock'), ...studentOnly }} />
      <Tabs.Screen name="ride" options={{ title: 'Request a ride', tabBarLabel: 'Ride', tabBarIcon: icon('bus'), ...studentOnly }} />
      <Tabs.Screen name="pass" options={{ title: 'Ride pass', tabBarLabel: 'Pass', tabBarIcon: icon('qr'), ...studentOnly }} />
      <Tabs.Screen name="queue" options={{ title: 'Ride queue', tabBarLabel: 'Queue', tabBarIcon: icon('list'), ...staffOnly }} />
      <Tabs.Screen name="scan" options={{ title: 'Scan pass', tabBarLabel: 'Scan', tabBarIcon: icon('scan'), ...staffOnly }} />
    </Tabs>
  );
}
