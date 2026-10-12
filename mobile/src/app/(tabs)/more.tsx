import { Link, type Href } from 'expo-router';
import { Pressable, Text, View } from 'react-native';

import { Button, Card, Screen, text } from '@/components/ui';
import { useAuth } from '@/lib/auth';
import { colors, space } from '@/lib/theme';

function Row({ href, label }: { href: Href; label: string }) {
  return (
    <Link href={href} asChild>
      <Pressable accessibilityRole="link" style={{ flexDirection: 'row', alignItems: 'center', paddingVertical: 14 }}>
        <Text style={[text.body, { flex: 1 }]}>{label}</Text>
        <Text style={{ color: colors.muted, fontSize: 20 }} accessibilityElementsHidden>›</Text>
      </Pressable>
    </Link>
  );
}

export default function More() {
  const { user, signOut } = useAuth();
  return (
    <Screen>
      <Card style={{ gap: 2 }}>
        <Text style={[text.body, { fontWeight: '600' }]}>{user?.name}</Text>
        <Text style={text.muted}>{user?.email} · {user?.role}</Text>
      </Card>
      <Card style={{ paddingVertical: 0, gap: 0 }}>
        <Row href="/about" label="About the team" />
        <View style={{ height: 1, backgroundColor: colors.border }} />
        <Row href="/terms" label="Terms and Conditions" />
      </Card>
      <View style={{ marginTop: space.md }}>
        <Button title="Sign out" variant="secondary" onPress={signOut} />
      </View>
    </Screen>
  );
}
