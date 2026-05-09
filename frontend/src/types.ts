export interface Metrics {
  co: number
  sv: number
  sys: number
  dia: number
  map_val: number
  pp: number
  lv_vol: number[]
  lvp: number[]
  lvof: number[]
  lvp_full: number[]
}

export interface SimResult {
  t: number[]
  X: number[][]        // [timeIdx][stateIdx]
  ecg: number[]
  preset: string
  params: Record<string, number | number[]>
  metrics: Metrics
  rr: number[] | null
}

export interface SimResponse {
  primary: SimResult
  comparison: SimResult | null
}

export interface PresetInfo {
  hr: number
  contract: number
  resist: number
  compl: number
  desc: string
  category: 'normal' | 'arrhythmia' | 'structural' | 'critical'
}

export type Presets = Record<string, PresetInfo>

export type Tab = 'monitor' | 'pvloop' | 'allvars' | 'export'
