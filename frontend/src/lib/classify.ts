export type Status = 'normal' | 'warning' | 'danger'

// Resting adult reference ranges. Outside `normal` is a warning; outside
// `limits` (where given) is marked as danger.
export interface Range { normal: [number, number]; limits: [number, number] }

export const RANGES: Record<string, Range> = {
  co:  { normal: [4.0, 8.0],  limits: [2.5, 10] },
  sv:  { normal: [60, 100],   limits: [30, 140] },
  sys: { normal: [90, 140],   limits: [80, 160] },
  dia: { normal: [60, 90],    limits: [50, 100] },
  map: { normal: [70, 105],   limits: [60, 120] },
  pp:  { normal: [25, 60],    limits: [20, 80] },
  ef:  { normal: [50, 70],    limits: [30, 80] },
  hr:  { normal: [60, 100],   limits: [40, 150] },
}

export function classify(name: string, value: number): Status {
  const r = RANGES[name]
  if (!r) return 'normal'
  if (value < r.limits[0] || value > r.limits[1]) return 'danger'
  if (value < r.normal[0] || value > r.normal[1]) return 'warning'
  return 'normal'
}

// 'Low' / 'High' label that accompanies a status colour, so state is never colour alone.
export function direction(name: string, value: number): 'Low' | 'High' | null {
  const r = RANGES[name]
  if (!r) return null
  if (value < r.normal[0]) return 'Low'
  if (value > r.normal[1]) return 'High'
  return null
}

export const STATUS_COLOR: Record<Status, string> = {
  normal:  '#18181b',
  warning: '#b45309',
  danger:  '#b91c1c',
}
