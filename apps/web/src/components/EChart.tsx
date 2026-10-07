import * as echarts from 'echarts'
import { useEffect, useRef } from 'react'
import type { EChartsOption } from 'echarts'

export function EChart({ option, className = '' }: { option: EChartsOption; className?: string }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!ref.current) return
    const chart = echarts.init(ref.current)
    chart.setOption(option)
    const resize = () => chart.resize()
    window.addEventListener('resize', resize)
    const observer = new ResizeObserver(resize)
    observer.observe(ref.current)
    return () => { observer.disconnect(); window.removeEventListener('resize', resize); chart.dispose() }
  }, [option])
  return <div ref={ref} className={`echart ${className}`} />
}

