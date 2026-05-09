import { useEffect, useRef } from 'react'
import uPlot from 'uplot'
import 'uplot/dist/uPlot.min.css'

interface Props {
  opts: Omit<uPlot.Options, 'width'>
  data: uPlot.AlignedData
  height: number
  className?: string
}

export function UPlotChart({ opts, data, height, className }: Props) {
  const wrapRef  = useRef<HTMLDivElement>(null)
  const plotRef  = useRef<uPlot | null>(null)
  const widthRef = useRef(0)

  // Create / destroy
  useEffect(() => {
    const el = wrapRef.current
    if (!el) return

    const w = el.clientWidth || 600
    widthRef.current = w

    const plot = new uPlot({ ...opts, width: w, height }, data, el)
    plotRef.current = plot

    const ro = new ResizeObserver(([entry]) => {
      const newW = Math.floor(entry.contentRect.width)
      if (newW !== widthRef.current && newW > 0) {
        widthRef.current = newW
        plotRef.current?.setSize({ width: newW, height })
      }
    })
    ro.observe(el)

    return () => {
      ro.disconnect()
      plot.destroy()
      plotRef.current = null
    }
    // intentionally omit opts/data from deps — handled below
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [height])

  // Update data without full destroy/recreate
  useEffect(() => {
    plotRef.current?.setData(data)
  }, [data])

  return (
    <div
      ref={wrapRef}
      className={className}
      style={{ width: '100%', height }}
    />
  )
}

// Shared cursor sync object — created once per sync key
const _syncs: Record<string, ReturnType<typeof uPlot.sync>> = {}
export function getSync(key: string) {
  if (!_syncs[key]) _syncs[key] = uPlot.sync(key)
  return _syncs[key]
}
