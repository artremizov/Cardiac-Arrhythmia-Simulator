import { useMemo } from 'react'
import uPlot from 'uplot'
import type { SimResult } from '../types'
import { SERIES, DASH_B, UPLOT_AXIS_X, UPLOT_AXIS_Y, SYNC_KEY } from '../lib/theme'
import { UPlotChart, getSync, windowed, interp, fmtValue, timeSeries, timeTicks } from '../lib/UPlotChart'

interface Props {
  primary: SimResult
  comparison: SimResult | null
  plotWindow: number
}

interface Trace { label: string; color: string; unit: string; get: (r: SimResult) => number[] }

interface Panel { yLabel: string; height: number; traces: Trace[]; digits: number }

const col = (r: SimResult, i: number) => r.X.map(row => row[i])

const PANELS: Panel[] = [
  {
    yLabel: 'ECG (a.u.)', height: 112, digits: 2,
    traces: [{ label: 'ECG', color: SERIES.ecg, unit: 'a.u.', get: r => r.ecg }],
  },
  {
    yLabel: 'Pressure (mmHg)', height: 200, digits: 1,
    traces: [
      { label: 'Aortic pressure', color: SERIES.aorta, unit: 'mmHg', get: r => col(r, 0) },
      { label: 'LV pressure',     color: SERIES.lv,    unit: 'mmHg', get: r => r.metrics.lvp_full },
    ],
  },
  {
    yLabel: 'Pressure (mmHg)', height: 152, digits: 1,
    traces: [
      { label: 'Systemic venous pressure',  color: SERIES.venous, unit: 'mmHg', get: r => col(r, 4) },
      { label: 'Pulmonary artery pressure', color: SERIES.pulm,   unit: 'mmHg', get: r => col(r, 6) },
    ],
  },
  {
    yLabel: 'Volume (mL)', height: 176, digits: 1,
    traces: [{ label: 'LV volume', color: SERIES.lv, unit: 'mL', get: r => col(r, 11) }],
  },
]

export function WaveformChart({ primary, comparison, plotWindow }: Props) {
  const hasComp = comparison !== null
  const tEnd    = primary.t[primary.t.length - 1]
  const tStart  = Math.max(0, tEnd - plotWindow)
  const sync    = useMemo(() => getSync(SYNC_KEY), [])

  const charts = useMemo(() => PANELS.map((panel, pi) => {
    const isLast = pi === PANELS.length - 1
    const [t, ...a] = windowed(primary.t, panel.traces.map(tr => tr.get(primary)), tStart, tEnd)
    const b = hasComp && comparison
      ? panel.traces.map(tr => interp(comparison.t, tr.get(comparison), t))
      : []

    const series: uPlot.Series[] = [
      timeSeries(),
      ...panel.traces.map(tr => ({
        label: hasComp ? `${tr.label} (A)` : tr.label,
        stroke: tr.color, width: 1.5, value: fmtValue(tr.unit, panel.digits),
      })),
      ...(hasComp ? panel.traces.map(tr => ({
        label: `${tr.label} (B)`,
        stroke: tr.color, width: 1.5, dash: DASH_B, value: fmtValue(tr.unit, panel.digits),
      })) : []),
    ]

    const opts: Omit<uPlot.Options, 'width'> = {
      height: panel.height,
      padding: [8, 16, 0, 0],
      cursor: { sync: { key: sync.key }, points: { show: false }, drag: { x: false, y: false } },
      legend: {
        show: true, live: true,
        markers: { dash: (_u: uPlot, i: number) => (hasComp && i > panel.traces.length ? 'dashed' : 'solid') },
      },
      series,
      axes: [
        isLast
          ? { ...UPLOT_AXIS_X, label: 'Time (s)', values: timeTicks }
          : { ...UPLOT_AXIS_X, size: 4, ticks: { show: false }, values: (_u: uPlot, v: number[]) => v.map(() => '') },
        { ...UPLOT_AXIS_Y, label: panel.yLabel },
      ],
      scales: { x: { time: false, range: [tStart, tEnd] } },
    }
    return { opts, data: [t, ...a, ...b] as uPlot.AlignedData, showTime: pi === 0 }
  }), [primary, comparison, hasComp, tStart, tEnd, sync.key])

  return (
    <div className="plot-stack">
      {hasComp && comparison && (
        <ConditionKey a={primary.preset} b={comparison.preset} />
      )}
      {charts.map((c, i) => (
        <UPlotChart key={i} opts={c.opts} data={c.data} className={c.showTime ? '' : 'hide-x-readout'} />
      ))}
    </div>
  )
}

// Line-style key for compare mode: colour is the quantity, dash is the condition
export function ConditionKey({ a, b }: { a: string; b: string }) {
  return (
    <div className="condition-key">
      <span><svg width="24" height="8"><line x1="0" y1="4" x2="24" y2="4" stroke={SERIES.ecg} strokeWidth="1.5" /></svg>A: {a}</span>
      <span><svg width="24" height="8"><line x1="0" y1="4" x2="24" y2="4" stroke={SERIES.ecg} strokeWidth="1.5" strokeDasharray={DASH_B.join(' ')} /></svg>B: {b}</span>
    </div>
  )
}
