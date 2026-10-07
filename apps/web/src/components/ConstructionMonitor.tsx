import { Activity, ArrowUpRight, CalendarClock, ChartNoAxesCombined } from 'lucide-react'
import { useMemo, useState } from 'react'
import type { EChartsOption } from 'echarts'
import type { Progress } from '../types'
import { formatDate, progressLabels } from '../utils/format'
import { EChart } from './EChart'

export function ConstructionMonitor({ rows, onOpen }: { rows: Progress[]; onOpen: (id: string) => void }) {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const selected = rows.find(row => row.id === selectedId) ?? rows.find(row => row.monthly_series.length > 0) ?? null
  const series = selected?.monthly_series ?? []
  const option = useMemo<EChartsOption>(() => ({
    animation: false, grid: { top: 26, left: 6, right: 12, bottom: 22, containLabel: true },
    legend: { top: 0, right: 0, itemWidth: 9, itemHeight: 3, textStyle: { color: '#687873', fontSize: 10 } }, tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: series.map(item => `${item.month.slice(5)}월`), axisTick: { show: false }, axisLine: { lineStyle: { color: '#dbe2df' } }, axisLabel: { color: '#74817d', fontSize: 9 } },
    yAxis: { type: 'value', min: 0, max: 100, axisLabel: { color: '#74817d', fontSize: 9, formatter: '{value}%' }, splitLine: { lineStyle: { color: '#edf1ef' } } },
    series: [
      { name: '계획', type: 'line', data: series.map(item => item.planned), symbolSize: 4, lineStyle: { color: '#82918c', type: 'dashed' }, itemStyle: { color: '#82918c' } },
      { name: '실제', type: 'line', data: series.map(item => item.actual), symbolSize: 4, lineStyle: { color: '#087b6b', width: 2 }, itemStyle: { color: '#087b6b' }, areaStyle: { color: 'rgba(8,123,107,.06)' } },
    ],
  }), [series])

  return <section className="section compact-progress" aria-labelledby="construction-title">
    <div className="section-heading compact-heading"><div><div className="eyebrow">CONSTRUCTION</div><h2 id="construction-title"><Activity size={16} /> 건설 공정 모니터링</h2></div><span className="section-subtitle">계획 대비 실제공정</span></div>
    <div className="compact-progress-body">
      <div className="progress-bullets">
        {rows.map(row => <button key={row.id} className={`progress-bullet ${selected?.id === row.id ? 'selected' : ''}`} onClick={() => setSelectedId(row.id)}>
          <div className="bullet-head"><strong>{row.project_name}</strong><span className={`progress-state state-${row.status.toLowerCase()}`}>{progressLabels[row.status]}</span></div>
          {row.actual_progress_rate === null ? <div className="bullet-missing"><b>공정률 데이터 미확보</b><small>0%로 집계하지 않음</small></div> : <><div className="bullet-values"><span>계획 <b>{row.planned_progress_rate}%</b></span><span>실제 <b>{row.actual_progress_rate}%</b></span><em className={(row.progress_gap ?? 0) < -5 ? 'negative' : ''}>{row.progress_gap}%p</em></div><div className="bullet-track"><i style={{ width: `${row.planned_progress_rate}%` }} /><b style={{ width: `${row.actual_progress_rate}%` }} /></div></>}
          <div className="bullet-date"><CalendarClock size={11} /> 준공 {formatDate(row.planned_completion_date)} <ArrowUpRight size={12} onClick={(event) => { event.stopPropagation(); onOpen(row.project_id) }} /></div>
        </button>)}
        {!rows.length && <div className="compact-empty">선택한 조건의 건설 사업이 없습니다.</div>}
      </div>
      <div className="selected-progress-chart"><div className="selected-chart-title"><ChartNoAxesCombined size={14} /><span>{selected?.project_name ?? '시계열 데이터'}</span>{selected && <small>{selected.actual_progress_rate === null ? '미확보' : `차이 ${selected.progress_gap}%p`}</small>}</div>{series.length ? <EChart option={option} /> : <div className="chart-empty">선택 사업의 월별 공정률 데이터 미확보</div>}</div>
    </div>
  </section>
}
