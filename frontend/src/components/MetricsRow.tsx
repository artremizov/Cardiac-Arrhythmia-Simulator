import type { SimResult } from '../types'
import { classify, STATUS_COLOR } from '../lib/classify'

interface MetricDef {
  key: string; label: string; unit: string
  value: (m: SimResult['metrics']) => number
  fmt: (v: number) => string
}

const METRICS: MetricDef[] = [
  { key: 'co',  label: 'Cardiac Output',     unit: 'L/min', value: m => m.co,      fmt: v => v.toFixed(2) },
  { key: 'sv',  label: 'Stroke Volume',      unit: 'mL',    value: m => m.sv,      fmt: v => v.toFixed(0) },
  { key: 'sys', label: 'Systolic BP',        unit: 'mmHg',  value: m => m.sys,     fmt: v => v.toFixed(0) },
  { key: 'dia', label: 'Diastolic BP',       unit: 'mmHg',  value: m => m.dia,     fmt: v => v.toFixed(0) },
  { key: 'map', label: 'Mean Art. Pressure', unit: 'mmHg',  value: m => m.map_val, fmt: v => v.toFixed(0) },
  { key: 'pp',  label: 'Pulse Pressure',     unit: 'mmHg',  value: m => m.pp,      fmt: v => v.toFixed(0) },
]

export function MetricsRow({ primary, comparison }: { primary: SimResult; comparison: SimResult | null }) {
  return (
    <div style={{
      display:      'flex',
      background:   '#ffffff',
      border:       '1px solid #e5e7eb',
      borderRadius: 8,
      overflow:     'hidden',
      marginBottom: 20,
    }}>
      {METRICS.map(({ key, label, unit, value, fmt }, i) => {
        const v1    = value(primary.metrics)
        const v2    = comparison ? value(comparison.metrics) : null
        const st    = classify(key, v1)
        const color = STATUS_COLOR[st]
        const delta = v2 != null && v1 !== 0 ? ((v2 - v1) / Math.abs(v1)) * 100 : null

        return (
          <div
            key={key}
            style={{
              flex:          1,
              padding:       '12px 14px',
              borderLeft:    i > 0 ? '1px solid #f1f5f9' : 'none',
              display:       'flex',
              flexDirection: 'column',
              gap:           3,
            }}
          >
            {/* Status dot + label */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <span style={{
                width: 5, height: 5, borderRadius: '50%',
                background: color, display: 'inline-block', flexShrink: 0,
              }} />
              <span style={{
                fontSize:      '0.65rem',
                fontWeight:    600,
                color:         '#94a3b8',
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
              }}>{label}</span>
            </div>

            {/* Value + delta */}
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
              <span style={{
                fontSize:   '1.3rem',
                fontWeight: 700,
                color,
                fontFamily: "'JetBrains Mono', Consolas, monospace",
                lineHeight: 1,
              }}>{fmt(v1)}</span>
              {delta != null && (
                <span style={{
                  fontSize:   '0.68rem',
                  fontWeight: 600,
                  color:      delta > 0 ? '#dc2626' : '#059669',
                }}>
                  {delta > 0 ? '+' : ''}{delta.toFixed(1)}%
                </span>
              )}
            </div>

            {/* Unit */}
            <span style={{ fontSize: '0.68rem', color: '#9ca3af' }}>{unit}</span>
          </div>
        )
      })}
    </div>
  )
}
