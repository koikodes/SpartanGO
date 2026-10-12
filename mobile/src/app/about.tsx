import { Stack } from 'expo-router';
import { ScrollView, Text, View } from 'react-native';

import { Card, text } from '@/components/ui';
import { advisor, course, department, mission, team } from '@/content/team';
import { colors, space } from '@/lib/theme';

function initials(name: string) {
  return name.split(/\s+/).map((p) => p[0]).slice(0, 2).join('').toUpperCase();
}

export default function AboutTeam() {
  return (
    <>
      <Stack.Screen options={{ headerShown: true, title: 'About the team', headerTintColor: colors.green }} />
      <ScrollView style={{ backgroundColor: colors.bg }} contentContainerStyle={{ padding: space.md, gap: space.md, paddingBottom: space.xl }}>
        <View style={{ gap: space.xs }}>
          <Text style={[text.h1, { color: colors.green }]}>SpartanGO</Text>
          <Text style={text.muted}>{course}</Text>
        </View>
        <Text style={[text.body, { lineHeight: 22 }]}>{mission}</Text>

        <Text style={text.h2} accessibilityRole="header">The team</Text>
        <Card style={{ gap: space.md }}>
          {team.map((m) => (
            <View key={m.name} style={{ flexDirection: 'row', alignItems: 'center', gap: space.md }}>
              <View
                accessibilityElementsHidden
                importantForAccessibility="no-hide-descendants"
                style={{ width: 44, height: 44, borderRadius: 22, backgroundColor: colors.green, alignItems: 'center', justifyContent: 'center' }}>
                <Text style={{ color: '#fff', fontWeight: '700' }}>{initials(m.name)}</Text>
              </View>
              <View style={{ flex: 1 }}>
                <Text style={[text.body, { fontWeight: '600' }]}>{m.name}</Text>
                {m.role ? <Text style={text.muted}>{m.role}</Text> : null}
              </View>
            </View>
          ))}
        </Card>

        <Text style={text.h2} accessibilityRole="header">Faculty advisor</Text>
        <Card>
          <Text style={[text.body, { fontWeight: '600' }]}>{advisor}</Text>
          <Text style={text.muted}>{department}</Text>
        </Card>

        <Text style={[text.muted, { textAlign: 'center' }]}>
          SpartanGO is a student prototype, not an official NSU service.
        </Text>
      </ScrollView>
    </>
  );
}
