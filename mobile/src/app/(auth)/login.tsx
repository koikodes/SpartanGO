import { Link } from 'expo-router';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, Text, View } from 'react-native';

import { Button, ErrorText, Field, Screen, text } from '@/components/ui';
import { useAuth } from '@/lib/auth';
import { colors, space } from '@/lib/theme';

export default function Login() {
  const { signIn } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      await signIn(email.trim(), password);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not sign in');
    } finally {
      setBusy(false);
    }
  };

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <Screen style={{ justifyContent: 'center', gap: space.lg }}>
        <View style={{ gap: space.xs }}>
          <Text style={[text.h1, { color: colors.green, fontSize: 40 }]}>SpartanGO</Text>
          <Text style={text.muted}>NSU shuttles, live.</Text>
        </View>
        <Field label="NSU email" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" autoComplete="email" placeholder="you@spartans.nsu.edu" />
        <Field label="Password" value={password} onChangeText={setPassword} secureTextEntry autoComplete="password" />
        <ErrorText>{error}</ErrorText>
        <Button title="Sign in" onPress={submit} loading={busy} disabled={!email || !password} />
        <Link href="/signup" style={{ color: colors.green, textAlign: 'center', fontWeight: '600' }}>
          New here? Create an account
        </Link>
        <View style={{ flexDirection: 'row', justifyContent: 'center', gap: space.lg }}>
          <Link href="/about" style={{ color: colors.muted }}>About the team</Link>
          <Link href="/terms" style={{ color: colors.muted }}>Terms</Link>
        </View>
      </Screen>
    </KeyboardAvoidingView>
  );
}
