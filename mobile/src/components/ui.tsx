import type { ReactNode } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View, type TextInputProps, type ViewStyle } from 'react-native';

import { colors, radius, space } from '@/lib/theme';

export function Screen({ children, style }: { children?: ReactNode; style?: ViewStyle }) {
  return <View style={[styles.screen, style]}>{children}</View>;
}

export function Card({ children, style }: { children: ReactNode; style?: ViewStyle }) {
  return <View style={[styles.card, style]}>{children}</View>;
}

export function Button({
  title, onPress, variant = 'primary', loading, disabled,
}: { title: string; onPress: () => void; variant?: 'primary' | 'secondary' | 'danger'; loading?: boolean; disabled?: boolean }) {
  const bg = variant === 'primary' ? colors.green : variant === 'danger' ? colors.danger : colors.card;
  const fg = variant === 'secondary' ? colors.green : '#fff';
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      disabled={disabled || loading}
      style={({ pressed }) => [
        styles.button,
        { backgroundColor: bg, opacity: disabled ? 0.5 : pressed ? 0.85 : 1 },
        variant === 'secondary' && { borderWidth: 1.5, borderColor: colors.green },
      ]}>
      {loading ? <ActivityIndicator color={fg} /> : <Text style={[styles.buttonText, { color: fg }]}>{title}</Text>}
    </Pressable>
  );
}

export function Field({ label, ...props }: TextInputProps & { label: string }) {
  return (
    <View style={{ gap: space.xs }}>
      <Text style={styles.label}>{label}</Text>
      <TextInput placeholderTextColor={colors.muted} style={styles.input} {...props} />
    </View>
  );
}

export function Chip({ label, selected, onPress, color }: { label: string; selected: boolean; onPress: () => void; color?: string }) {
  const c = color ?? colors.green;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected }}
      onPress={onPress}
      style={[styles.chip, { borderColor: c, backgroundColor: selected ? c : colors.card }]}>
      <Text style={{ color: selected ? '#fff' : c, fontWeight: '600' }}>{label}</Text>
    </Pressable>
  );
}

export function ErrorText({ children }: { children: ReactNode }) {
  return children ? <Text style={{ color: colors.danger }}>{children}</Text> : null;
}

export const text = StyleSheet.create({
  h1: { fontSize: 28, fontWeight: '800', color: colors.text },
  h2: { fontSize: 20, fontWeight: '700', color: colors.text },
  body: { fontSize: 16, color: colors.text },
  muted: { fontSize: 14, color: colors.muted },
});

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg, padding: space.md, gap: space.md },
  card: { backgroundColor: colors.card, borderRadius: radius.md, padding: space.md, borderWidth: 1, borderColor: colors.border, gap: space.sm },
  button: { borderRadius: radius.md, paddingVertical: 14, alignItems: 'center', justifyContent: 'center', minHeight: 50 },
  buttonText: { fontSize: 16, fontWeight: '700' },
  label: { fontSize: 14, fontWeight: '600', color: colors.text },
  input: { backgroundColor: colors.card, borderWidth: 1, borderColor: colors.border, borderRadius: radius.sm, padding: 12, fontSize: 16, color: colors.text },
  chip: { borderWidth: 1.5, borderRadius: 999, paddingHorizontal: 14, paddingVertical: 8 },
});
