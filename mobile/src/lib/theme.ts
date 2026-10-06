// NSU green & gold. One place to change the look of the whole app.
export const colors = {
  green: '#007A53',
  greenDark: '#00563A',
  gold: '#F2A900',
  bg: '#F6F7F5',
  card: '#FFFFFF',
  text: '#1B1F1D',
  muted: '#5E6862',
  border: '#E1E5E2',
  danger: '#C62828',
  success: '#2E7D32',
};

export const space = { xs: 4, sm: 8, md: 16, lg: 24, xl: 32 };
export const radius = { sm: 8, md: 12, lg: 20 };

export function formatEta(seconds: number): string {
  if (seconds < 45) return 'Arriving';
  const min = Math.round(seconds / 60);
  return `${min} min`;
}
