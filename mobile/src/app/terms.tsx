import { Stack } from 'expo-router';
import { ScrollView, Text, View } from 'react-native';

import { text } from '@/components/ui';
import { advisor, contactEmail, department } from '@/content/team';
import { TERMS_UPDATED, terms, termsIntro } from '@/content/terms';
import { colors, space } from '@/lib/theme';

export default function Terms() {
  return (
    <>
      <Stack.Screen options={{ headerShown: true, title: 'Terms and Conditions', headerTintColor: colors.green }} />
      <ScrollView style={{ backgroundColor: colors.bg }} contentContainerStyle={{ padding: space.md, gap: space.md, paddingBottom: space.xl }}>
        <Text style={text.muted}>Last updated {TERMS_UPDATED}</Text>
        <Text style={text.body}>{termsIntro}</Text>
        {terms.map((s) => (
          <View key={s.title} style={{ gap: space.xs }}>
            <Text style={[text.h2, { fontSize: 18 }]} accessibilityRole="header">{s.title}</Text>
            {s.body.map((p) => (
              <Text key={p} style={[text.body, { lineHeight: 22 }]}>{p}</Text>
            ))}
          </View>
        ))}
        <View style={{ gap: space.xs }}>
          <Text style={[text.h2, { fontSize: 18 }]} accessibilityRole="header">11. Contact</Text>
          <Text style={[text.body, { lineHeight: 22 }]}>
            {contactEmail
              ? `Questions or deletion requests: ${contactEmail}`
              : `Questions or deletion requests: contact the SpartanGO team through our advisor, ${advisor}, ${department}.`}
          </Text>
        </View>
      </ScrollView>
    </>
  );
}
