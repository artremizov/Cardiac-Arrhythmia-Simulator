// Clinical color palette — muted, professional, light-theme
export const C = {
  // Waveform traces
  ecg:    '#059669',   // emerald-600
  aortic: '#dc2626',   // red-600
  lvp:    '#d97706',   // amber-600 (dashed)
  venous: '#2563eb',   // blue-600
  pulm:   '#7c3aed',   // violet-600
  volume: '#4f46e5',   // indigo-600 (filled)

  // Compare mode
  comp1:  '#0284c7',   // sky-600
  comp2:  '#e11d48',   // rose-600

  // PV loop
  pv:     '#2563eb',
  ref:    '#94a3b8',   // ESPVR reference

  // Chart chrome
  grid:   '#f1f5f9',
  axis:   '#e2e8f0',
  text:   '#94a3b8',
  bg:     '#f9fafb',
}

export const PALETTE: string[] = [
  '#dc2626','#d97706','#059669','#2563eb','#7c3aed',
  '#db2777','#4f46e5','#0891b2','#ea580c','#65a30d',
  '#64748b','#0284c7',
]

// Axis configuration shared across all uPlot instances
export const UPLOT_AXIS_X = {
  stroke:     C.text,
  ticks:      { stroke: C.axis, width: 1 },
  grid:       { stroke: C.grid, width: 1 },
  font:       '10px Inter, system-ui, sans-serif',
  labelFont:  '11px Inter, system-ui, sans-serif',
  labelSize:  16,
  gap:        4,
}

export const UPLOT_AXIS_Y = {
  stroke:     C.text,
  ticks:      { stroke: C.axis, width: 1 },
  grid:       { stroke: C.grid, width: 1 },
  font:       '10px Inter, system-ui, sans-serif',
  labelFont:  '11px Inter, system-ui, sans-serif',
  labelSize:  20,
  gap:        4,
  size:       54,
}

export const SYNC_KEY = 'cardiosim-monitor'
