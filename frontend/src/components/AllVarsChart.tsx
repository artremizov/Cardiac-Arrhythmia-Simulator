import { useState, useMemo } from 'react'
import uPlot from 'uplot'
import type { SimResult } from '../types'
import { C, PALETTE, UPLOT_AXIS_X, UPLOT_AXIS_Y } from '../lib/theme'
import { UPlotChart } from '../lib/UPlotChart'

const STATE_LABELS: [string, string][] = [
  ['Aortic Pressure',              'mmHg'],
  ['Aortic Flow',                  'cm³/s'],
  ['Systemic Arterial Pressure',   'mmHg'],
  ['Systemic Peripheral Flow',     'cm³/s'],
  ['Systemic Venous Pressure',     'mmHg'],
  ['Right Ventricle Volume',       'cm³'],
  ['Pulmonary Artery Pressure',    'mmHg'],
  ['Pulmonary Arterial Flow',      'cm³/s'],
  ['Pulmonary Arteriole Pressure', 'mmHg'],
  ['Pulmonary Venous Flow',        'cm³/s'],
  ['Pulm. Venous / LA Pressure',   'mmHg'],
  ['Left Ventricle Volume',        'cm³'],
]

interface Props {
  primary: SimResult
  comparison: SimResult | null
  plotWindow: number
}

function buildVarData(
  p: SimResult,
  c: SimResult | null,
  varIdx: number,
  tStart: number,
  tEnd: number,
): uPlot.AlignedData {
  const step = Math.max(1, Math.floor(p.t.length / 1800))
  const idxs: number[] = []
  for (let i = 0; i < p.t.length; i += step) {
    if (p.t[i] >= tStart && p.t[i] <= tEnd) idxs.push(i)
  }
  const t  = idxs.map(i => p.t[i])
  const v1 = idxs.map(i => p.X[i][varIdx])
  if (!c) return [t, v1]

  // Interpolate comparison onto primary's time grid
  let j = 0
  const v2 = t.map(gt => {
    while (j < c.t.length - 1 && c.t[j + 1] < gt) j++
    if (j >= c.t.length - 1) return c.X[c.t.length - 1][varIdx]
    const a = c.t[j], b = c.t[j + 1]
    const alpha = b === a ? 0 : (gt - a) / (b - a)
    return c.X[j][varIdx] + alpha * (c.X[j + 1][varIdx] - c.X[j][varIdx])
  })
  return [t, v1, v2]
}

export function AllVarsChart({ primary, comparison, plotWindow }: Props) {
  const [selected, setSelected] = useState<number[]>([0, 4, 6, 11])
  const hasComp = comparison !== null

  const tEnd   = primary.t[primary.t.length - 1]
  const tStart = Math.max(0, tEnd - plotWindow)

  const panels = useMemo(() =>
    selected.map((vi, rowIdx) => ({
      vi,
      isLast: rowIdx === selected.length - 1,
      data: buildVarData(primary, comparison, vi, tStart, tEnd),
    })),
  [selected, primary, comparison, tStart, tEnd])

  const toggle = (i: number) =>
    setSelected(prev =>
      prev.includes(i) ? prev.filter(x => x !== i) : [...prev, i].sort((a, b) => a - b)
    )

  return (
    <div>
      {/* Variable selector */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 18 }}>
        {STATE_LABELS.map(([name], i) => {
          const on    = selected.includes(i)
          const color = PALETTE[i]
          return (
            <button
              key={i}
              onClick={() => toggle(i)}
              style={{
                padding: '3px 10px',
                borderRadius: 5,
                fontSize: '0.72rem',
                fontWeight: 500,
                cursor: 'pointer',
                transition: 'all 0.12s',
                background: on ? color + '14' : '#f8fafc',
                border: `1px solid ${on ? color + '60' : '#e2e8f0'}`,
                color: on ? color : '#64748b',
                fontFamily: 'Inter, system-ui, sans-serif',
              }}
            >
              X{i + 1} · {name.split(' ')[0]}
            </button>
          )
        })}
      </div>

      {selected.length === 0 ? (
        <p style={{ color: '#9ca3af', textAlign: 'center', padding: '48px 0', fontSize: 13 }}>
          Select at least one variable above.
        </p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {panels.map(({ vi, isLast, data }) => {
            const [name, unit] = STATE_LABELS[vi]
            const color = hasComp ? C.comp1 : PALETTE[vi]

            const series: uPlot.Series[] = [
              {},
              { stroke: color, width: 1.5, label: hasComp ? 'Primary' : name },
              ...(hasComp ? [{ stroke: C.comp2, width: 1.5, label: 'Comparison' }] : []),
            ]

            const opts: Omit<uPlot.Options, 'width'> = {
              height:  130,
              padding: [4, 12, 0, 0],
              cursor:  { points: { show: false } },
              legend:  { show: false },
              series,
              axes: [
                {
                  ...UPLOT_AXIS_X,
                  show:   isLast,
                  label:  isLast ? 'Time (s)' : undefined,
                  values: (_u: uPlot, vals: number[]) => vals.map(v => v.toFixed(1)),
                },
                {
                  ...UPLOT_AXIS_Y,
                  label: unit,
                },
              ],
              scales: {
                x: { time: false, range: [tStart, tEnd] as [number, number] },
              },
            }

            return (
              <div key={vi}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3, paddingLeft: 4, height: 20 }}>
                  <span style={{
                    fontSize: '0.68rem', fontWeight: 600, color: '#64748b',
                    letterSpacing: '0.06em', textTransform: 'uppercase',
                  }}>
                    X{vi + 1} — {name}
                  </span>
                  <span style={{ width: 16, height: 2, background: PALETTE[vi], display: 'inline-block', borderRadius: 1 }} />
                </div>
                <UPlotChart opts={opts} data={data} height={130} />
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
