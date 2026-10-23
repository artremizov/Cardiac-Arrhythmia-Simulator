import { useEffect, useRef, useState, useMemo } from 'react'
import type { SimResult } from '../types'
import { SERIES, DASH_B, CHART, UI, FONT } from '../lib/theme'
import { ConditionKey } from './WaveformChart'

interface Props {
  primary: SimResult
  comparison: SimResult | null
}

function niceTicks(min: number, max: number, target = 6): number[] {
  const range = max - min || 1
  const raw   = range / (target - 1)
  const mag   = Math.pow(10, Math.floor(Math.log10(raw)))
  const step  = [1, 2, 2.5, 5, 10].map(n => n * mag).find(s => s >= raw) ?? mag
  const start = Math.ceil(min / step) * step
  const ticks: number[] = []
  for (let v = start; v <= max + step * 0.01; v += step) ticks.push(+v.toFixed(10))
  return ticks
}

function path(pts: [number, number][], close = false): string {
  if (!pts.length) return ''
  const d = pts.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
  return close ? d + ' Z' : d
}

// Loop summary from the plotted beat. Stroke work is the enclosed area (shoelace).
function loopStats(r: SimResult) {
  const v = r.metrics.lv_vol, p = r.metrics.lvp
  if (v.length < 3) return null
  const edv = Math.max(...v), esv = Math.min(...v)
  let area = 0
  for (let i = 0; i < v.length; i++) {
    const j = (i + 1) % v.length
    area += v[i] * p[j] - v[j] * p[i]
  }
  return { edv, esv, sv: edv - esv, ef: (edv - esv) / edv * 100, sw: Math.abs(area) / 2 }
}

const num = (x: number | number[] | undefined) => (typeof x === 'number' ? x : NaN)

interface HoverInfo { x: number; y: number; vol: number; pres: number }

const H = 420
const PAD = { l: 56, r: 16, t: 8, b: 44 }

export function PVLoopChart({ primary, comparison }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [W, setW]    = useState(640)
  const [hover, setHover] = useState<HoverInfo | null>(null)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const ro = new ResizeObserver(([e]) => setW(Math.max(240, Math.floor(e.contentRect.width))))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const statsA = useMemo(() => loopStats(primary), [primary])
  const statsB = useMemo(() => (comparison ? loopStats(comparison) : null), [comparison])

  const chart = useMemo(() => {
    const vol1 = primary.metrics.lv_vol, pres1 = primary.metrics.lvp
    if (vol1.length < 3) return null
    const vol2 = comparison?.metrics.lv_vol ?? [], pres2 = comparison?.metrics.lvp ?? []

    const allVol  = [...vol1, ...vol2]
    const allPres = [...pres1, ...pres2]
    const xMin = Math.max(0, Math.min(...allVol) - 15)
    const xMax = Math.max(...allVol) + 15
    const yMax = Math.max(...allPres) * 1.15

    const plotW = W - PAD.l - PAD.r
    const plotH = H - PAD.t - PAD.b
    const sx = (v: number) => PAD.l + (v - xMin) / (xMax - xMin) * plotW
    const sy = (p: number) => PAD.t + plotH - p / yMax * plotH

    // Passive LV pressure-volume relation of the model (activation A = 0): P = ELD·V
    const ELD = num(primary.params.ELD)
    const passive = (v: number) => ELD * v

    // Loop corners: end-systole is the top of the minimum-volume limb, end-diastole the bottom of the maximum-volume limb
    const vMax = Math.max(...vol1), vMin = Math.min(...vol1), tol = 0.005 * (vMax - vMin)
    const idx = vol1.map((_, i) => i)
    const esIdx = idx.filter(i => vol1[i] <= vMin + tol).reduce((b, i) => (pres1[i] > pres1[b] ? i : b))
    const edIdx = idx.filter(i => vol1[i] >= vMax - tol).reduce((b, i) => (pres1[i] < pres1[b] ? i : b))

    // Direction marker a quarter of the way through the beat
    const ai = Math.min(Math.floor(vol1.length * 0.25), vol1.length - 2)
    const angle = Math.atan2(sy(pres1[ai + 1]) - sy(pres1[ai]), sx(vol1[ai + 1]) - sx(vol1[ai])) * 180 / Math.PI

    return {
      plotW, plotH, sx, sy, xMin, xMax, yMax,
      xTicks: niceTicks(xMin, xMax), yTicks: niceTicks(0, yMax),
      vol1, pres1, vol2, pres2, passive, edIdx, esIdx,
      arrow: { x: sx(vol1[ai]), y: sy(pres1[ai]), angle },
    }
  }, [W, primary, comparison])

  const onMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!chart) return
    const rect = e.currentTarget.getBoundingClientRect()
    const mx = e.clientX - rect.left, my = e.clientY - rect.top
    let best = Infinity, bi = 0
    for (let i = 0; i < chart.vol1.length; i++) {
      const d = (chart.sx(chart.vol1[i]) - mx) ** 2 + (chart.sy(chart.pres1[i]) - my) ** 2
      if (d < best) { best = d; bi = i }
    }
    setHover(Math.sqrt(best) < 32
      ? { x: chart.sx(chart.vol1[bi]), y: chart.sy(chart.pres1[bi]), vol: chart.vol1[bi], pres: chart.pres1[bi] }
      : null)
  }

  const txt = { fontSize: 11, fill: CHART.text, fontFamily: FONT }

  return (
    <div className="pv-layout">
      <div className="pv-plot">
        {comparison
          ? <ConditionKey a={primary.preset} b={comparison.preset} />
          : (
            <div className="condition-key">
              <span><svg width="24" height="8"><line x1="0" y1="4" x2="24" y2="4" stroke={SERIES.lv} strokeWidth="2" /></svg>LV pressure–volume loop</span>
              <span><svg width="24" height="8"><line x1="0" y1="4" x2="24" y2="4" stroke={UI.muted} strokeWidth="1" strokeDasharray="2 3" /></svg>Passive filling relation of the model, P = ELD·V</span>
            </div>
          )}
        <div ref={containerRef} style={{ position: 'relative' }}>
          {chart ? (
            <>
              <svg width={W} height={H} style={{ display: 'block', cursor: 'crosshair' }}
                   onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
                <defs>
                  <clipPath id="pv-clip"><rect x={PAD.l} y={PAD.t} width={chart.plotW} height={chart.plotH} /></clipPath>
                </defs>

                {chart.xTicks.map(v => (
                  <line key={`gx${v}`} x1={chart.sx(v)} x2={chart.sx(v)} y1={PAD.t} y2={PAD.t + chart.plotH} stroke={CHART.grid} />
                ))}
                {chart.yTicks.map(p => (
                  <line key={`gy${p}`} x1={PAD.l} x2={PAD.l + chart.plotW} y1={chart.sy(p)} y2={chart.sy(p)} stroke={CHART.grid} />
                ))}

                <g clipPath="url(#pv-clip)">
                  {!comparison && (
                    <line x1={chart.sx(chart.xMin)} y1={chart.sy(chart.passive(chart.xMin))}
                          x2={chart.sx(chart.xMax)} y2={chart.sy(chart.passive(chart.xMax))}
                          stroke={UI.muted} strokeWidth={1} strokeDasharray="2 3" />
                  )}
                  {comparison && chart.vol2.length > 2 && (
                    <path d={path(chart.vol2.map((v, i) => [chart.sx(v), chart.sy(chart.pres2[i])] as [number, number]), true)}
                          stroke={SERIES.lv} strokeWidth={1.5} strokeDasharray={DASH_B.join(' ')} fill="none" />
                  )}
                  <path d={path(chart.vol1.map((v, i) => [chart.sx(v), chart.sy(chart.pres1[i])] as [number, number]), true)}
                        stroke={SERIES.lv} strokeWidth={2} strokeLinejoin="round" fill="none" />
                </g>

                <polygon points="-5,-3.5 5,0 -5,3.5" fill={SERIES.lv}
                         transform={`translate(${chart.arrow.x},${chart.arrow.y}) rotate(${chart.arrow.angle})`} />

                {[{ i: chart.esIdx, label: 'ESV', dx: -8, dy: -8, anchor: 'end' },
                  { i: chart.edIdx, label: 'EDV', dx: 8, dy: 16, anchor: 'start' }].map(m => (
                  <g key={m.label}>
                    <circle cx={chart.sx(chart.vol1[m.i])} cy={chart.sy(chart.pres1[m.i])} r={4}
                            fill={SERIES.lv} stroke={UI.surface} strokeWidth={2} />
                    <text x={chart.sx(chart.vol1[m.i]) + m.dx} y={chart.sy(chart.pres1[m.i]) + m.dy}
                          textAnchor={m.anchor as 'start' | 'end'} {...txt} fill={UI.ink2}>{m.label}</text>
                  </g>
                ))}

                <line x1={PAD.l} x2={PAD.l + chart.plotW} y1={PAD.t + chart.plotH} y2={PAD.t + chart.plotH} stroke={CHART.axis} />
                <line x1={PAD.l} x2={PAD.l} y1={PAD.t} y2={PAD.t + chart.plotH} stroke={CHART.axis} />
                {chart.xTicks.map(v => (
                  <text key={`tx${v}`} x={chart.sx(v)} y={PAD.t + chart.plotH + 16} textAnchor="middle" {...txt}>{v.toFixed(0)}</text>
                ))}
                {chart.yTicks.map(p => (
                  <text key={`ty${p}`} x={PAD.l - 8} y={chart.sy(p) + 4} textAnchor="end" {...txt}>{p.toFixed(0)}</text>
                ))}
                <text x={PAD.l + chart.plotW / 2} y={H - 6} textAnchor="middle" {...txt} fontSize={12}>LV volume (mL)</text>
                <text x={14} y={PAD.t + chart.plotH / 2} textAnchor="middle" {...txt} fontSize={12}
                      transform={`rotate(-90, 14, ${PAD.t + chart.plotH / 2})`}>LV pressure (mmHg)</text>

                {hover && (
                  <circle cx={hover.x} cy={hover.y} r={4} fill={SERIES.lv} stroke={UI.surface} strokeWidth={2} />
                )}
              </svg>
              {hover && (
                <div className="tooltip" style={{ left: hover.x + 12, top: Math.max(0, hover.y - 40) }}>
                  <div>Volume <span className="num">{hover.vol.toFixed(1)}</span> mL</div>
                  <div>Pressure <span className="num">{hover.pres.toFixed(1)}</span> mmHg</div>
                </div>
              )}
            </>
          ) : (
            <p className="empty-note">Not enough data for a pressure–volume loop. Increase the duration.</p>
          )}
        </div>
      </div>

      <aside className="pv-side">
        <table className="data-table">
          <thead>
            <tr><th></th><th>{comparison ? 'A' : 'Value'}</th>{comparison && <th>B</th>}<th>Unit</th></tr>
          </thead>
          <tbody>
            {([
              ['End-diastolic volume', 'edv', 0, 'mL'],
              ['End-systolic volume',  'esv', 0, 'mL'],
              ['Stroke volume',        'sv',  1, 'mL'],
              ['Ejection fraction',    'ef',  1, '%'],
              ['Stroke work',          'sw',  0, 'mmHg·mL'],
            ] as [string, 'edv' | 'esv' | 'sv' | 'ef' | 'sw', number, string][]).map(([label, k, d, unit]) => (
              <tr key={k}>
                <td>{label}</td>
                <td className="num">{statsA ? statsA[k].toFixed(d) : '–'}</td>
                {comparison && <td className="num">{statsB ? statsB[k].toFixed(d) : '–'}</td>}
                <td className="unit">{unit}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="note">
          Values are from the plotted beat: the last full beat, or for AF and VF the beat with the
          median stroke volume. Stroke work is the area enclosed by the loop.
        </p>
        <p className="note">
          The loop runs counter-clockwise: filling along the bottom, isovolumic contraction on the
          right, ejection across the top, isovolumic relaxation on the left.
        </p>
      </aside>
    </div>
  )
}
