import { useState, useMemo } from 'react'
import uPlot from 'uplot'
import type { SimResult } from '../types'
import { DASH_B, UPLOT_AXIS_X, UPLOT_AXIS_Y } from '../lib/theme'
import { STATE_VARS } from '../lib/stateVars'
import { UPlotChart, getSync, windowed, interp, fmtValue, timeSeries, timeTicks } from '../lib/UPlotChart'
import { ConditionKey } from './WaveformChart'

const QUANTITY: Record<string, string> = { mmHg: 'Pressure', 'mL/s': 'Flow', mL: 'Volume' }

interface Props {
  primary: SimResult
  comparison: SimResult | null
  plotWindow: number
}

export function AllVarsChart({ primary, comparison, plotWindow }: Props) {
  const [selected, setSelected] = useState<number[]>([0, 4, 6, 11])
  const hasComp = comparison !== null
  const sync    = useMemo(() => getSync('cardiosim-allvars'), [])

  const tEnd   = primary.t[primary.t.length - 1]
  const tStart = Math.max(0, tEnd - plotWindow)

  const charts = useMemo(() => selected.map((vi, row) => {
    const v = STATE_VARS[vi]
    const isLast = row === selected.length - 1
    const [t, a] = windowed(primary.t, [primary.X.map(r => r[vi])], tStart, tEnd, 1800)
    const b = hasComp && comparison ? [interp(comparison.t, comparison.X.map(r => r[vi]), t)] : []
    const opts: Omit<uPlot.Options, 'width'> = {
      height: isLast ? 160 : 128,
      padding: [8, 16, 0, 0],
      cursor: { sync: { key: sync.key }, points: { show: false }, drag: { x: false, y: false } },
      legend: {
        show: true, live: true,
        markers: { dash: (_u: uPlot, i: number) => (i === 2 ? 'dashed' : 'solid') },
      },
      series: [
        timeSeries(),
        { label: `${v.id} ${v.name}${hasComp ? ' (A)' : ''}`, stroke: v.color, width: 1.5, value: fmtValue(v.unit) },
        ...(hasComp ? [{ label: `${v.id} ${v.name} (B)`, stroke: v.color, width: 1.5, dash: DASH_B, value: fmtValue(v.unit) }] : []),
      ],
      axes: [
        isLast
          ? { ...UPLOT_AXIS_X, label: 'Time (s)', values: timeTicks }
          : { ...UPLOT_AXIS_X, size: 4, ticks: { show: false }, values: (_u: uPlot, x: number[]) => x.map(() => '') },
        { ...UPLOT_AXIS_Y, label: `${QUANTITY[v.unit]} (${v.unit})` },
      ],
      scales: { x: { time: false, range: [tStart, tEnd] } },
    }
    return { vi, opts, data: [t, a, ...b] as uPlot.AlignedData, showTime: row === 0 }
  }), [selected, primary, comparison, hasComp, tStart, tEnd, sync.key])

  const toggle = (i: number) =>
    setSelected(prev => (prev.includes(i) ? prev.filter(x => x !== i) : [...prev, i].sort((a, b) => a - b)))

  return (
    <div className="allvars">
      <fieldset className="var-picker">
        <legend>State variables</legend>
        {STATE_VARS.map((v, i) => (
          <label key={v.id}>
            <input type="checkbox" checked={selected.includes(i)} onChange={() => toggle(i)} />
            <span className="var-id">{v.id}</span>
            <span>{v.name}</span>
            <span className="unit">{v.unit}</span>
          </label>
        ))}
        <div className="var-actions">
          <button type="button" className="link-btn" onClick={() => setSelected(STATE_VARS.map((_, i) => i))}>Select all</button>
          <button type="button" className="link-btn" onClick={() => setSelected([])}>Clear</button>
        </div>
      </fieldset>

      <div className="plot-stack" style={{ minWidth: 0 }}>
        {hasComp && comparison && <ConditionKey a={primary.preset} b={comparison.preset} />}
        {selected.length === 0
          ? <p className="empty-note">Select one or more state variables.</p>
          : charts.map(c => (
              <UPlotChart key={c.vi} opts={c.opts} data={c.data} className={c.showTime ? '' : 'hide-x-readout'} />
            ))}
      </div>
    </div>
  )
}
