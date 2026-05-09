import { useEffect, useRef, useState, useMemo } from 'react'
import type { SimResult } from '../types'
import { C } from '../lib/theme'

interface Props {
  primary: SimResult
  comparison: SimResult | null
}

function niceTicks(min: number, max: number, target = 5): number[] {
  const range = max - min || 1
  const raw   = range / (target - 1)
  const mag   = Math.pow(10, Math.floor(Math.log10(raw)))
  const step  = [1, 2, 2.5, 5, 10].map(n => n * mag).find(s => s >= raw) ?? mag
  const start = Math.ceil(min / step) * step
  const ticks: number[] = []
  for (let v = start; v <= max + step * 0.01; v += step) ticks.push(+v.toFixed(10))
  return ticks
}

function polyPath(pts: [number, number][], close = false): string {
  if (!pts.length) return ''
  const d = pts.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
  return close ? d + ' Z' : d
}

interface HoverInfo { svgX: number; svgY: number; vol: number; pres: number }

export function PVLoopChart({ primary, comparison }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [W, setW]    = useState(560)
  const [hover, setHover] = useState<HoverInfo | null>(null)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const ro = new ResizeObserver(([e]) => setW(Math.max(200, Math.floor(e.contentRect.width))))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const chart = useMemo(() => {
    // The backend's calculate_metrics already isolates exactly one representative
    // cardiac cycle into lv_vol / lvp — use them directly.
    const vol1  = primary.metrics.lv_vol  as number[]
    const pres1 = primary.metrics.lvp     as number[]

    // Log so we can verify lengths in the browser console
    console.log('[PVLoop] primary cycle pts:', vol1.length,
      '| comparison:', comparison ? (comparison.metrics.lv_vol as number[]).length : 'none')

    if (vol1.length < 3) return null

    const vol2  = comparison ? comparison.metrics.lv_vol as number[] : []
    const pres2 = comparison ? comparison.metrics.lvp     as number[] : []

    const hasComp = comparison !== null

    const H     = 400
    const pad   = { l: 64, r: 16, t: 16, b: 50 }
    const plotW = W - pad.l - pad.r
    const plotH = H - pad.t - pad.b

    const allVol  = [...vol1, ...vol2]
    const allPres = [...pres1, ...pres2]
    const xMin = Math.min(...allVol)  * 0.90
    const xMax = Math.max(...allVol)  * 1.08
    const yMin = 0
    const yMax = Math.max(...allPres) * 1.20

    const sx = (v: number) => pad.l + (v - xMin) / (xMax - xMin) * plotW
    const sy = (p: number) => pad.t + plotH - (p - yMin) / (yMax - yMin) * plotH

    // ESV = index of highest pressure near minimum volume
    const esv = Math.min(...vol1)
    const edv = Math.max(...vol1)
    const rng = edv - esv

    const nearESV = vol1.map((_, i) => i).filter(i => vol1[i] < esv + 0.05 * rng)
    const espIdx  = nearESV.length
      ? nearESV.reduce((b, i) => pres1[i] > pres1[b] ? i : b, nearESV[0])
      : 0

    const nearEDV = vol1.map((_, i) => i).filter(i => vol1[i] > edv - 0.05 * rng)
    const edpIdx  = nearEDV.length
      ? nearEDV.reduce((b, i) => pres1[i] < pres1[b] ? i : b, nearEDV[0])
      : vol1.length - 1

    const v0      = 10
    const ees     = pres1[espIdx] / (vol1[espIdx] - v0 || 1)
    const espVMax = Math.min(v0 + yMax / ees, edv + 10)
    const edvP    = pres1[edpIdx]
    const loop1color = hasComp ? C.comp1 : C.pv
    const sw = Math.round((edv - esv) * (primary.metrics.map_val ?? 0))

    // Direction arrow ~25 % through the cycle (ejection phase)
    const ai = Math.min(Math.floor(vol1.length * 0.25), vol1.length - 2)
    const arrowAngle = Math.atan2(
      sy(pres1[ai + 1]) - sy(pres1[ai]),
      sx(vol1[ai + 1])  - sx(vol1[ai]),
    ) * 180 / Math.PI

    return {
      H, pad, plotW, plotH, sx, sy,
      xTicks: niceTicks(xMin, xMax, 6),
      yTicks: niceTicks(yMin, yMax, 6),
      vol1, pres1, vol2, pres2, hasComp,
      espIdx, edpIdx, esv, edv, v0, ees, espVMax, edvP,
      loop1color, sw,
      arrow: { x: sx(vol1[ai]), y: sy(pres1[ai]), angle: arrowAngle },
    }
  }, [W, primary, comparison])

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!chart) return
    const rect = e.currentTarget.getBoundingClientRect()
    const mx = e.clientX - rect.left
    const my = e.clientY - rect.top
    let bestDist = Infinity, bestIdx = 0
    for (let i = 0; i < chart.vol1.length; i++) {
      const d = (chart.sx(chart.vol1[i]) - mx) ** 2 + (chart.sy(chart.pres1[i]) - my) ** 2
      if (d < bestDist) { bestDist = d; bestIdx = i }
    }
    if (Math.sqrt(bestDist) < 32) {
      setHover({
        svgX: chart.sx(chart.vol1[bestIdx]),
        svgY: chart.sy(chart.pres1[bestIdx]),
        vol:  chart.vol1[bestIdx],
        pres: chart.pres1[bestIdx],
      })
    } else {
      setHover(null)
    }
  }

  return (
    <div className="flex gap-8">
      <div ref={containerRef} className="flex-1 min-w-0" style={{ position: 'relative' }}>
        {chart ? (
          <>
            <svg
              width={W} height={chart.H}
              style={{ display: 'block', overflow: 'visible', cursor: 'crosshair' }}
              onMouseMove={handleMouseMove}
              onMouseLeave={() => setHover(null)}
            >
              <rect x={chart.pad.l} y={chart.pad.t} width={chart.plotW} height={chart.plotH} fill="#f9fafb" rx="2" />

              {chart.xTicks.map(v => (
                <line key={v} x1={chart.sx(v)} x2={chart.sx(v)} y1={chart.pad.t} y2={chart.pad.t + chart.plotH} stroke="#e5e7eb" strokeWidth={1} />
              ))}
              {chart.yTicks.map(p => (
                <line key={p} x1={chart.pad.l} x2={chart.pad.l + chart.plotW} y1={chart.sy(p)} y2={chart.sy(p)} stroke="#e5e7eb" strokeWidth={1} />
              ))}

              {/* Comparison loop (behind primary) */}
              {chart.hasComp && chart.vol2.length > 2 && (
                <path
                  d={polyPath(chart.vol2.map((v, i) =>
                    [chart.sx(v), chart.sy(chart.pres2[i])] as [number, number]
                  ), true)}
                  stroke={C.comp2} strokeWidth={2.0} fill={C.comp2} fillOpacity={0.06}
                />
              )}

              {/* Primary loop */}
              <path
                d={polyPath(chart.vol1.map((v, i) =>
                  [chart.sx(v), chart.sy(chart.pres1[i])] as [number, number]
                ), true)}
                stroke={chart.loop1color} strokeWidth={2.2} fill={chart.loop1color} fillOpacity={0.07}
              />

              {/* Direction arrow */}
              <polygon
                points="-5,-3 5,0 -5,3"
                fill={chart.loop1color} fillOpacity={0.9}
                transform={`translate(${chart.arrow.x},${chart.arrow.y}) rotate(${chart.arrow.angle})`}
              />

              {/* ESPVR */}
              <line x1={chart.sx(chart.v0)} y1={chart.sy(0)} x2={chart.sx(chart.espVMax)} y2={chart.sy(chart.ees * (chart.espVMax - chart.v0))} stroke={C.ref} strokeWidth={1.2} strokeDasharray="5 3" />
              <text x={chart.sx(chart.espVMax) + 4} y={chart.sy(chart.ees * (chart.espVMax - chart.v0)) + 4} fontSize={9} fill="#94a3b8" fontFamily="Inter, system-ui, sans-serif">ESPVR</text>

              {/* EDP reference */}
              <line x1={chart.sx(chart.esv - 1)} y1={chart.sy(chart.edvP)} x2={chart.sx(chart.edv + 2)} y2={chart.sy(chart.edvP)} stroke={C.ref} strokeWidth={1} strokeDasharray="2 4" />

              {/* ESV */}
              <circle cx={chart.sx(chart.vol1[chart.espIdx])} cy={chart.sy(chart.pres1[chart.espIdx])} r={4} fill="#fff" stroke={chart.loop1color} strokeWidth={1.8} />
              <text x={chart.sx(chart.vol1[chart.espIdx]) - 6} y={chart.sy(chart.pres1[chart.espIdx]) - 8} textAnchor="end" fontSize={10} fill="#6b7280" fontFamily="Inter, system-ui, sans-serif">ESV</text>

              {/* EDV */}
              <circle cx={chart.sx(chart.vol1[chart.edpIdx])} cy={chart.sy(chart.pres1[chart.edpIdx])} r={4} fill="#fff" stroke={chart.loop1color} strokeWidth={1.8} />
              <text x={chart.sx(chart.vol1[chart.edpIdx]) + 6} y={chart.sy(chart.pres1[chart.edpIdx]) + 13} textAnchor="start" fontSize={10} fill="#6b7280" fontFamily="Inter, system-ui, sans-serif">EDV</text>

              <text x={chart.pad.l + chart.plotW / 2} y={chart.pad.t + chart.plotH * 0.38} textAnchor="middle" fontSize={10} fill="#9ca3af" fontFamily="Inter, system-ui, sans-serif">SW ≈ {chart.sw} mmHg·mL</text>

              {/* Axes */}
              <line x1={chart.pad.l} x2={chart.pad.l + chart.plotW} y1={chart.pad.t + chart.plotH} y2={chart.pad.t + chart.plotH} stroke="#d1d5db" strokeWidth={1} />
              <line x1={chart.pad.l} x2={chart.pad.l} y1={chart.pad.t} y2={chart.pad.t + chart.plotH} stroke="#d1d5db" strokeWidth={1} />

              {chart.xTicks.map(v => (
                <g key={v}>
                  <line x1={chart.sx(v)} x2={chart.sx(v)} y1={chart.pad.t + chart.plotH} y2={chart.pad.t + chart.plotH + 4} stroke="#d1d5db" strokeWidth={1} />
                  <text x={chart.sx(v)} y={chart.pad.t + chart.plotH + 16} textAnchor="middle" fontSize={10} fill="#9ca3af" fontFamily="Inter, system-ui, sans-serif">{v.toFixed(0)}</text>
                </g>
              ))}
              {chart.yTicks.map(p => (
                <g key={p}>
                  <line x1={chart.pad.l - 4} x2={chart.pad.l} y1={chart.sy(p)} y2={chart.sy(p)} stroke="#d1d5db" strokeWidth={1} />
                  <text x={chart.pad.l - 8} y={chart.sy(p) + 4} textAnchor="end" fontSize={10} fill="#9ca3af" fontFamily="Inter, system-ui, sans-serif">{p.toFixed(0)}</text>
                </g>
              ))}

              <text x={chart.pad.l + chart.plotW / 2} y={chart.H - 6} textAnchor="middle" fontSize={11} fill="#6b7280" fontFamily="Inter, system-ui, sans-serif">LV Volume (cm³)</text>
              <text x={16} y={chart.pad.t + chart.plotH / 2} textAnchor="middle" fontSize={11} fill="#6b7280" fontFamily="Inter, system-ui, sans-serif" transform={`rotate(-90, 16, ${chart.pad.t + chart.plotH / 2})`}>LV Pressure (mmHg)</text>

              {hover && (
                <>
                  <line x1={hover.svgX} x2={hover.svgX} y1={chart.pad.t} y2={chart.pad.t + chart.plotH} stroke="#cbd5e1" strokeWidth={1} strokeDasharray="3 3" />
                  <line x1={chart.pad.l} x2={chart.pad.l + chart.plotW} y1={hover.svgY} y2={hover.svgY} stroke="#cbd5e1" strokeWidth={1} strokeDasharray="3 3" />
                  <circle cx={hover.svgX} cy={hover.svgY} r={5} fill="white" stroke={chart.loop1color} strokeWidth={2} />
                </>
              )}
            </svg>

            {hover && (
              <div style={{
                position: 'absolute', left: hover.svgX + 14,
                top: Math.max(chart.pad.t, hover.svgY - 30),
                background: '#ffffff', border: '1px solid #e5e7eb', borderRadius: 5,
                padding: '5px 10px', fontSize: 11, lineHeight: 1.7,
                boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
                fontFamily: "'JetBrains Mono', Consolas, monospace",
                pointerEvents: 'none', zIndex: 10, color: '#374151',
              }}>
                <div>V: <strong>{hover.vol.toFixed(1)}</strong> cm³</div>
                <div>P: <strong>{hover.pres.toFixed(1)}</strong> mmHg</div>
              </div>
            )}
          </>
        ) : (
          <div style={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <p style={{ color: '#9ca3af', fontSize: 13 }}>Insufficient data for PV loop</p>
          </div>
        )}
      </div>

      {/* Educational sidebar */}
      <div style={{ width: 196, flexShrink: 0, fontSize: 12, paddingTop: 8 }}>
        <p style={{ fontWeight: 600, color: '#374151', marginBottom: 12 }}>PV Loop Phases</p>
        {[
          ['① Isovolumic Contraction', 'Valves closed — pressure rises steeply at fixed volume.'],
          ['② Ejection',               'Aortic valve opens — volume falls as blood is ejected.'],
          ['③ Isovolumic Relaxation',  'Aortic valve closes — pressure drops at fixed volume.'],
          ['④ Diastolic Filling',      'Mitral valve opens — volume increases at low pressure.'],
        ].map(([title, desc]) => (
          <div key={title} style={{ marginBottom: 12 }}>
            <p style={{ color: '#374151', fontWeight: 500, marginBottom: 3 }}>{title}</p>
            <p style={{ color: '#6b7280', lineHeight: 1.5 }}>{desc}</p>
          </div>
        ))}
        <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: 12, marginTop: 4 }}>
          <p style={{ color: '#9ca3af', marginBottom: 6 }}>
            <span style={{ color: '#6b7280', fontWeight: 500 }}>ESPVR — </span>end-systolic P–V relationship
          </p>
          <p style={{ color: '#9ca3af', marginBottom: 6 }}>
            <span style={{ color: '#6b7280', fontWeight: 500 }}>EDV line — </span>end-diastolic pressure level
          </p>
          <p style={{ color: '#9ca3af' }}>
            <span style={{ color: '#6b7280', fontWeight: 500 }}>SW — </span>stroke work ≈ SV × MAP
          </p>
        </div>
        {chart && (
          <div style={{ marginTop: 16, padding: '8px 12px', background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 6 }}>
            <p style={{ color: '#9ca3af', fontSize: 10, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 6 }}>Primary Loop</p>
            {([
              ['ESV', chart.esv.toFixed(0) + ' cm³'],
              ['EDV', chart.edv.toFixed(0) + ' cm³'],
              ['SV',  (chart.edv - chart.esv).toFixed(0) + ' cm³'],
              ['SW',  chart.sw + ' mmHg·mL'],
            ] as [string, string][]).map(([k, v]) => (
              <div key={k} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                <span style={{ color: '#9ca3af' }}>{k}</span>
                <span style={{ color: '#374151', fontFamily: "'JetBrains Mono', monospace", fontWeight: 500 }}>{v}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
