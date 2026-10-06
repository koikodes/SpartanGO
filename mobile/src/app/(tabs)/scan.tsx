import { CameraView, useCameraPermissions, type BarcodeScanningResult } from 'expo-camera';
import { useRef, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { Button, Screen, text } from '@/components/ui';
import { api } from '@/lib/api';
import { colors, space } from '@/lib/theme';
import type { PassCheck } from '@/lib/types';

/** Driver view: scan a student's rotating QR pass and show a big green/red result. */
export default function ScanPass() {
  const [permission, requestPermission] = useCameraPermissions();
  const [result, setResult] = useState<PassCheck | null>(null);
  const busy = useRef(false);

  const onScan = async ({ data }: BarcodeScanningResult) => {
    if (busy.current || result) return;
    busy.current = true;
    try {
      setResult(await api.verifyPass(data));
    } catch (e) {
      setResult({ valid: false, reason: e instanceof Error ? e.message : 'Check failed' });
    } finally {
      busy.current = false;
    }
  };

  if (!permission) return <Screen />;
  if (!permission.granted) {
    return (
      <Screen style={{ justifyContent: 'center' }}>
        <Text style={text.body}>Camera access is needed to scan ride passes.</Text>
        <Button title="Allow camera" onPress={requestPermission} />
      </Screen>
    );
  }

  if (result) {
    return (
      <View style={[styles.result, { backgroundColor: result.valid ? colors.success : colors.danger }]}>
        <Text style={styles.big}>{result.valid ? '✓ Valid pass' : '✕ Not valid'}</Text>
        <Text style={styles.detail}>{result.valid ? result.name : result.reason}</Text>
        <View style={{ alignSelf: 'stretch' }}>
          <Button title="Scan next" variant="secondary" onPress={() => setResult(null)} />
        </View>
      </View>
    );
  }

  return (
    <View style={{ flex: 1 }}>
      <CameraView style={StyleSheet.absoluteFill} facing="back" barcodeScannerSettings={{ barcodeTypes: ['qr'] }} onBarcodeScanned={onScan} />
      <View style={styles.hint}><Text style={{ color: '#fff', fontWeight: '600' }}>Point at the student's pass</Text></View>
    </View>
  );
}

const styles = StyleSheet.create({
  result: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: space.lg, gap: space.lg },
  big: { fontSize: 40, fontWeight: '800', color: '#fff' },
  detail: { fontSize: 22, color: '#fff', textAlign: 'center' },
  hint: { position: 'absolute', bottom: space.xl, alignSelf: 'center', backgroundColor: '#000a', paddingHorizontal: 16, paddingVertical: 10, borderRadius: 999 },
});
