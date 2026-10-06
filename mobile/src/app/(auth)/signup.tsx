import { Link } from 'expo-router';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, Text } from 'react-native';

import { Button, ErrorText, Field, text } from '@/components/ui';
import { useAuth } from '@/lib/auth';
import { colors, space } from '@/lib/theme';

export default function Signup() {
  const { signUp } = useAuth();
  const [form, setForm] = useState({ name: '', email: '', student_id: '', password: '' });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const set = (k: keyof typeof form) => (v: string) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      await signUp({ ...form, email: form.email.trim() });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not create account');
    } finally {
      setBusy(false);
    }
  };

  const ready = form.name && form.email && form.student_id && form.password.length >= 8;

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView style={{ backgroundColor: colors.bg }} contentContainerStyle={{ padding: space.md, paddingTop: 80, gap: space.md }}>
        <Text style={text.h1}>Create your account</Text>
        <Text style={text.muted}>Use your NSU email. Your ride pass replaces showing your ID.</Text>
        <Field label="Full name" value={form.name} onChangeText={set('name')} autoComplete="name" />
        <Field label="NSU email" value={form.email} onChangeText={set('email')} autoCapitalize="none" keyboardType="email-address" />
        <Field label="Student ID" value={form.student_id} onChangeText={set('student_id')} autoCapitalize="none" />
        <Field label="Password (8+ characters)" value={form.password} onChangeText={set('password')} secureTextEntry autoComplete="new-password" />
        <ErrorText>{error}</ErrorText>
        <Button title="Create account" onPress={submit} loading={busy} disabled={!ready} />
        <Link href="/login" style={{ color: colors.green, textAlign: 'center', fontWeight: '600' }}>
          Already have an account? Sign in
        </Link>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
