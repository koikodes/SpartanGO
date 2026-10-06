import type { ColorValue } from 'react-native';
import Svg, { Circle, Path, Rect } from 'react-native-svg';

export type IconName = 'map' | 'clock' | 'bus' | 'qr' | 'list' | 'scan' | 'bell' | 'bellOff';

/** Small stroke icons drawn with react-native-svg (no icon-font dependency). */
export function Icon({ name, color, size = 24 }: { name: IconName; color: ColorValue; size?: number }) {
  const p = { stroke: color, strokeWidth: 2, fill: 'none', strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      {name === 'map' && (<><Path {...p} d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21z" /><Circle {...p} cx={12} cy={9.5} r={2.5} /></>)}
      {name === 'clock' && (<><Circle {...p} cx={12} cy={12} r={9} /><Path {...p} d="M12 7v5l3 2" /></>)}
      {name === 'bus' && (<><Rect {...p} x={4} y={3} width={16} height={15} rx={3} /><Path {...p} d="M4 11h16M7 21v-3M17 21v-3" /><Circle cx={8} cy={14.5} r={1.2} fill={color} /><Circle cx={16} cy={14.5} r={1.2} fill={color} /></>)}
      {name === 'qr' && (<><Rect {...p} x={3} y={3} width={7} height={7} /><Rect {...p} x={14} y={3} width={7} height={7} /><Rect {...p} x={3} y={14} width={7} height={7} /><Path {...p} d="M14 14h3v3M21 14v7h-4M14 18v3" /></>)}
      {name === 'list' && (<Path {...p} d="M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01" />)}
      {name === 'scan' && (<Path {...p} d="M3 8V5a2 2 0 0 1 2-2h3M16 3h3a2 2 0 0 1 2 2v3M21 16v3a2 2 0 0 1-2 2h-3M8 21H5a2 2 0 0 1-2-2v-3M7 12h10" />)}
      {name === 'bell' && (<Path {...p} d="M6 16V11a6 6 0 1 1 12 0v5l2 2H4l2-2zM10 21h4" />)}
      {name === 'bellOff' && (<Path {...p} d="M6 16V11a6 6 0 0 1 9.5-4.9M18 11v5l2 2H8M10 21h4M3 3l18 18" />)}
    </Svg>
  );
}
