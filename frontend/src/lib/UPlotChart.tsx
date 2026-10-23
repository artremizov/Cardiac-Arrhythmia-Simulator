import { useEffect, useRef } from 'react'
import uPlot from 'uplot'
import 'uplot/dist/uPlot.min.css'

interface Props {
  opts: Omit<uPlot.Options, 'width'>   // memoise in the caller; a new object rebuilds the chart
  data: uPlot.AlignedData
  className?: string
}

export function UPlotChart({ opts, data, className }: Props) {
  const wrapRef  = useRef<HTMLDivElement>(null)
  const plotRef  = useRef<uPlot | null>(null)
  const dataRef  = useRef(data)
  dataRef.current = data

  // Create / destroy whenever the options change (series count, ranges, sizes)
  useEffect(() => {
    const el = wrapRef.current
    if (!el) return

    let width = Math.floor(el.clientWidth) || 600
    const plot = new uPlot({ ...opts, width }, dataRef.current, el)
    plotRef.current = plot

    const ro = new ResizeObserver(([entry]) => {
      const w = Math.floor(entry.contentRect.width)
      if (w > 0 && w !== width) {
        width = w
        plot.setSize({ width: w, height: opts.height })
      }
    })
    ro.observe(el)

    return () => {
      ro.disconnect()
      plot.destroy()
      plotRef.current = null
    }
  }, [opts])

  // New data with the same options: update in place
  useEffect(() => {
    plotRef.current?.setData(data)
  }, [data])

  return <div ref={wrapRef} className={className} style={{ width: '100%' }} />
}

// Shared cursor sync object, one per key
const _syncs: Record<string, ReturnType<typeof uPlot.sync>> = {}
export function getSync(key: string) {
  if (!_syncs[key]) _syncs[key] = uPlot.sync(key)
  return _syncs[key]
}

// Keep the last `seconds` of a run and thin it to at most maxPts points
export function windowed(
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
  return [idxs.map(i => t[i]), ...arrays.map(arr => idxs.map(i => arr[i]))]
}

// Linear interpolation of (srcT, srcV) onto dstT; used to put run B on run A's time grid
export function interp(srcT: number[], srcV: number[], dstT: number[]): number[] {
  let j = 0
  return dstT.map(gt => {
    while (j < srcT.length - 1 && srcT[j + 1] < gt) j++
    if (j >= srcT.length - 1) return srcV[srcT.length - 1]
    const t0 = srcT[j], t1 = srcT[j + 1]
    const alpha = t1 === t0 ? 0 : (gt - t0) / (t1 - t0)
    return srcV[j] + alpha * (srcV[j + 1] - srcV[j])
  })
}

// Time-axis tick labels with as many decimals as the tick spacing needs (0.25 s -> 2)
export function timeTicks(_u: uPlot, splits: number[], _ax: number, _space: number, incr: number): string[] {
  const decimals = (String(+incr.toFixed(6)).split('.')[1] ?? '').length
  return splits.map(v => v.toFixed(decimals))
}

// Legend readouts: empty until the cursor is over the plot
export function fmtValue(unit: string, digits = 1) {
  return (_u: uPlot, v: number | null) => (v == null ? '' : `${v.toFixed(digits)} ${unit}`)
}

// x series: no label (an empty element; uPlot would substitute "Value" for ''), time on hover
export function timeSeries(): uPlot.Series {
  return {
    label: document.createElement('span'),
    value: (_u, v) => (v == null ? '' : `t = ${v.toFixed(3)} s`),
  }
}
