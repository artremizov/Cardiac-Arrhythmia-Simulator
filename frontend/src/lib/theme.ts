// Design tokens. The UI is neutral grays plus one accent; status colours are
// reserved for metrics outside their reference range.
export const UI = {
  ink:       '#18181b',
  ink2:      '#52525b',
  muted:     '#71717a',
  border:    '#e4e4e7',
  borderStr: '#d4d4d8',
  surface:   '#ffffff',
  page:      '#fafafa',
  accent:    '#1f5fbf',
  warning:   '#b45309',
  danger:    '#b91c1c',
}

export const FONT = "Inter, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"

// One colour per quantity, the same in every plot. Okabe-Ito blue, vermillion
// and bluish green plus Tol's wine: checked for colour-vision deficiency.
export const SERIES = {
  aorta:  '#0072B2',
  lv:     '#D55E00',
  venous: '#009E73',
  pulm:   '#882255',
  ecg:    '#3f3f46',
  other:  '#71717a',
}

// Condition B in compare mode: same colour as A, dashed.
export const DASH_B = [5, 4]

// Chart chrome
export const CHART = {
  grid: '#eeeef0',
  axis: '#d4d4d8',
  text: '#71717a',
  font: `11px ${FONT}`,
  labelFont: `12px ${FONT}`,
}

export const UPLOT_AXIS_X = {
  stroke:    CHART.text,
  ticks:     { stroke: CHART.axis, width: 1, size: 4 },
  grid:      { stroke: CHART.grid, width: 1 },
  font:      CHART.font,
  labelFont: CHART.labelFont,
  labelSize: 24,
  gap:       4,
  size:      32,
}

export const UPLOT_AXIS_Y = {
  stroke:    CHART.text,
  ticks:     { stroke: CHART.axis, width: 1, size: 4 },
  grid:      { stroke: CHART.grid, width: 1 },
  font:      CHART.font,
  labelFont: CHART.labelFont,
  labelSize: 24,
  gap:       4,
  size:      48,
}

export const SYNC_KEY = 'cardiosim-monitor'
