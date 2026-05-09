import { useMemo } from 'react'
import uPlot from 'uplot'
import type { SimResult } from '../types'
import { C, UPLOT_AXIS_X, UPLOT_AXIS_Y, SYNC_KEY } from '../lib/theme'
import { UPlotChart, getSync } from '../lib/UPlotChart'

interface Props {
  primary: SimResult
  comparison: SimResult | null
  plotWindow: number
}

// Downsample aligned arrays to at most maxPts points in [tStart, tEnd]
function window(
  t: number[],
  arrays: number[][],
  tStart: number,
  tEnd: number,
  maxPts = 2000,
): [number[], ...number[][]] {
  const inRange: number[] = []
  for (let i = 0; i < t.length; i++) {
    if (t[i] >= tStart && t[i] <= tEnd) inRange.push(i)
  }
  const step = Math.max(1, Math.floor(inRange.length / maxPts))
  const idxs = inRange.filter((_, j) => j % step === 0)
  return [
    idxs.map(i => t[i]),
    ...arrays.map(arr => idxs.map(i => arr[i])),
  ]
}

// Interpolate values from source time array onto a target time array
function interp(srcT: number[], srcV: number[], dstT: number[]): number[] {
  let j = 0
  return dstT.map(gt => {
    while (j < srcT.length - 1 && srcT[j + 1] < gt) j++
    if (j >= srcT.length - 1) return srcV[srcT.length - 1]
    const t0 = srcT[j], t1 = srcT[j + 1]
    const alpha = t1 === t0 ? 0 : (gt - t0) / (t1 - t0)
    return srcV[j] + alpha * (srcV[j + 1] - srcV[j])
  })
}

interface PanelDef {
  label: string
  dots: { color: string; label: string; dashed?: boolean }[]
  yLabel: string
  height: number
  showXAxis: boolean
  buildData: (
    p: SimResult,
    c: SimResult | null,
    hasComp: boolean,
    tStart: number,
    tEnd: number,
  ) => uPlot.AlignedData
  buildSeries: (hasComp: boolean) => uPlot.Series[]
}

const PANELS: PanelDef[] = [
  {
    label: 'ECG (Lead II)',
    dots: [{ color: C.ecg, label: 'ECG' }],
    yLabel: 'mV',
    height: 120,
    showXAxis: false,
    buildData(p, c, hasComp, tStart, tEnd) {
      const [t, ecg1] = window(p.t, [p.ecg], tStart, tEnd)
      if (!hasComp || !c) return [t, ecg1]
      const ecg2 = interp(c.t, c.ecg, t)
      return [t, ecg1, ecg2]
    },
    buildSeries(hasComp) {
      return [
        {},
        { stroke: hasComp ? C.comp1 : C.ecg, width: 1.5, label: 'ECG' },
        ...(hasComp ? [{ stroke: C.comp2, width: 1.5, label: 'Compare' }] : []),
      ]
    },
  },
  {
    label: 'Arterial Pressures',
    dots: [
      { color: C.aortic, label: 'Aortic' },
      { color: C.lvp, label: 'LV Pressure', dashed: true },
    ],
    yLabel: 'mmHg',
    height: 160,
    showXAxis: false,
    buildData(p, c, hasComp, tStart, tEnd) {
      const aortic1 = p.X.map(row => row[0])
      const lvp1    = p.metrics.lvp_full
      const [t, ao1, lv1] = window(p.t, [aortic1, lvp1], tStart, tEnd)
      if (!hasComp || !c) return [t, ao1, lv1]
      const ao2 = interp(c.t, c.X.map(r => r[0]), t)
      const lv2 = interp(c.t, c.metrics.lvp_full, t)
      return [t, ao1, lv1, ao2, lv2]
    },
    buildSeries(hasComp) {
      return [
        {},
        { stroke: hasComp ? C.comp1 : C.aortic, width: 1.8, label: 'Aortic' },
        { stroke: hasComp ? C.comp1 : C.lvp,    width: 1.2, label: 'LV Pres.', dash: [4, 3] },
        ...(hasComp ? [
          { stroke: C.comp2, width: 1.8, label: 'Aortic (B)' },
          { stroke: C.comp2, width: 1.2, label: 'LV Pres. (B)', dash: [4, 3] },
        ] : []),
      ]
    },
  },
  {
    label: 'Venous & Pulmonary',
    dots: [
      { color: C.venous, label: 'Systemic Venous' },
      { color: C.pulm,   label: 'Pulmonary Artery' },
    ],
    yLabel: 'mmHg',
    height: 130,
    showXAxis: false,
    buildData(p, c, hasComp, tStart, tEnd) {
      const ven1  = p.X.map(row => row[4])
      const pulm1 = p.X.map(row => row[6])
      const [t, v1, pm1] = window(p.t, [ven1, pulm1], tStart, tEnd)
      if (!hasComp || !c) return [t, v1, pm1]
      const v2  = interp(c.t, c.X.map(r => r[4]), t)
      const pm2 = interp(c.t, c.X.map(r => r[6]), t)
      return [t, v1, pm1, v2, pm2]
    },
    buildSeries(hasComp) {
      return [
        {},
        { stroke: hasComp ? C.comp1 : C.venous, width: 1.5, label: 'Venous' },
        { stroke: hasComp ? C.comp1 : C.pulm,   width: 1.5, label: 'Pulm. Artery' },
        ...(hasComp ? [
          { stroke: C.comp2, width: 1.5, label: 'Venous (B)' },
          { stroke: C.comp2, width: 1.5, label: 'Pulm. (B)' },
        ] : []),
      ]
    },
  },
  {
    label: 'LV Volume',
    dots: [{ color: C.volume, label: 'LV Volume' }],
    yLabel: 'cm³',
    height: 130,
    showXAxis: true,
    buildData(p, c, hasComp, tStart, tEnd) {
      const vol1 = p.X.map(row => row[11])
      const [t, v1] = window(p.t, [vol1], tStart, tEnd)
      if (!hasComp || !c) return [t, v1]
      const v2 = interp(c.t, c.X.map(r => r[11]), t)
      return [t, v1, v2]
    },
    buildSeries(hasComp) {
      return [
        {},
        {
          stroke: hasComp ? C.comp1 : C.volume,
          width: 1.7,
          label: 'LV Volume',
          fill: hasComp ? 'rgba(2,132,199,0.07)' : 'rgba(79,70,229,0.08)',
        },
        ...(hasComp ? [{
          stroke: C.comp2,
          width: 1.4,
          label: 'LV Vol. (B)',
          fill: 'rgba(225,29,72,0.06)',
        }] : []),
      ]
    },
  },
]

export function MonitorChart({ primary, comparison, plotWindow }: Props) {
  const hasComp = comparison !== null
  const tEnd    = primary.t[primary.t.length - 1]
  const tStart  = Math.max(0, tEnd - plotWindow)

  const sync = useMemo(() => getSync(SYNC_KEY), [])

  const panels = useMemo(() =>
    PANELS.map(panel => ({
      data:   panel.buildData(primary, comparison, hasComp, tStart, tEnd),
      series: panel.buildSeries(hasComp),
    })),
  [primary, comparison, hasComp, tStart, tEnd])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {PANELS.map((panel, pi) => {
        const { data, series } = panels[pi]
        const dots = hasComp
          ? [
              { color: C.comp1, label: 'Primary' },
              { color: C.comp2, label: 'Comparison' },
            ]
          : panel.dots

        const opts: Omit<uPlot.Options, 'width'> = {
          height:  panel.height,
          padding: [4, 12, 0, 0],
          cursor:  { sync: { key: sync.key }, points: { show: false } },
          legend:  { show: false },
          series,
          axes: [
            {
              ...UPLOT_AXIS_X,
              show:   panel.showXAxis,
              label:  panel.showXAxis ? 'Time (s)' : undefined,
              values: (_u: uPlot, vals: number[]) => vals.map(v => v.toFixed(1)),
            },
            {
              ...UPLOT_AXIS_Y,
              label: panel.yLabel,
            },
          ],
          scales: {
            x: { time: false, range: [tStart, tEnd] as [number, number] },
          },
        }

        return (
          <div key={pi}>
            {/* Panel header */}
            <div className="flex items-center gap-3 mb-1 px-1" style={{ height: 22 }}>
              <span style={{ fontSize: '0.7rem', fontWeight: 600, color: '#64748b', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                {panel.label}
              </span>
              <div className="flex items-center gap-2.5">
                {dots.map(dot => (
                  <span key={dot.label} className="flex items-center gap-1">
                    <svg width="18" height="8">
                      {(dot as any).dashed
                        ? <line x1="0" y1="4" x2="18" y2="4" stroke={dot.color} strokeWidth="1.5" strokeDasharray="4 2" />
                        : <line x1="0" y1="4" x2="18" y2="4" stroke={dot.color} strokeWidth="2" />
                      }
                    </svg>
                    <span style={{ fontSize: '0.62rem', color: '#9ca3af' }}>{dot.label}</span>
                  </span>
                ))}
              </div>
            </div>

            {/* Chart */}
            <UPlotChart opts={opts} data={data} height={panel.height} />
          </div>
        )
      })}
    </div>
  )
}
