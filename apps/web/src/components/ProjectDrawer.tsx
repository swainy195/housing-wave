import { Calendar, ChevronRight, Database, ExternalLink, House, MapPin, X } from 'lucide-react'
import { useMemo } from 'react'
import type { EChartsOption } from 'echarts'
import type { ProjectDetail } from '../types'
import { formatDate, formatUnits, progressLabels, stageLabels } from '../utils/format'
import { EChart } from './EChart'
import { StatusBadge } from './StatusBadge'

export function ProjectDrawer({ project, loading, onClose }: { project: ProjectDetail | null; loading: boolean; onClose: () => void }) {
  const series = project?.construction_progress?.monthly_series ?? []
  const option = useMemo<EChartsOption>(() => ({
    grid: { top: 28, left: 8, right: 14, bottom: 24, containLabel: true },
    tooltip: { trigger: 'axis' },
    legend: { top: 0, right: 0, itemWidth: 10, itemHeight: 3, textStyle: { fontSize: 10 } },
    xAxis: { type: 'category', data: series.map(s => s.month.slice(5) + '월'), axisTick: { show: false }, axisLine: { lineStyle: { color: '#d8dedb' } } },
    yAxis: { type: 'value', axisLabel: { formatter: '{value}%' }, splitLine: { lineStyle: { color: '#eef1ef' } } },
    series: [
      { name: '계획', type: 'line', data: series.map(s => s.planned), symbolSize: 6, lineStyle: { color: '#86938e', type: 'dashed' }, itemStyle: { color: '#86938e' } },
      { name: '실제', type: 'line', data: series.map(s => s.actual), symbolSize: 6, lineStyle: { color: '#087b6b', width: 3 }, itemStyle: { color: '#087b6b' }, areaStyle: { color: 'rgba(8,123,107,.08)' } },
    ],
  }), [series])

  return (
    <div className={`drawer-shell ${project || loading ? 'open' : ''}`} aria-hidden={!project && !loading}>
      <button className="drawer-backdrop" onClick={onClose} aria-label="상세 패널 닫기" />
      <aside className="project-drawer" aria-label="사업 상세">
        <button className="drawer-close" onClick={onClose}><X size={20} /></button>
        {loading && <div className="drawer-loading"><span /><p>사업 상세를 불러오는 중입니다</p></div>}
        {project && !loading && <>
          <div className="drawer-eyebrow"><span>{project.is_demo ? 'DEMO PROJECT' : 'LIVE PROJECT'}</span><StatusBadge status={project.data_status} /></div>
          <h2>{project.name}</h2>
          <div className="drawer-location"><MapPin size={14} /> {project.address}</div>
          <div className="drawer-kpis">
            <div><span>기관</span><strong>{project.organization}</strong></div>
            <div><span>계획 물량</span><strong>{formatUnits(project.planned_units)}</strong></div>
            <div><span>현재 단계</span><strong>{stageLabels[project.current_stage]}</strong></div>
          </div>

          <div className="drawer-section">
            <h3><Calendar size={16} /> 단계별 타임라인</h3>
            <div className="timeline">
              {project.timeline.length ? project.timeline.map(event => (
                <div className="timeline-item" key={event.id}>
                  <span className={`timeline-dot ${event.status.toLowerCase()}`} />
                  <div><b>{stageLabels[event.stage]} · {event.event_type.replaceAll('_', ' ')}</b><small>계획 {formatDate(event.planned_date)} · 실제 {formatDate(event.actual_date)}</small></div>
                  {event.delay_days !== null && event.delay_days > 0 && <em>+{event.delay_days}일</em>}
                </div>
              )) : <div className="drawer-empty">타임라인 데이터 미확보</div>}
            </div>
          </div>

          <div className="drawer-section">
            <h3><House size={16} /> 공정 현황</h3>
            {project.construction_progress ? <>
              <div className="drawer-progress-head">
                <div><span>계획</span><b>{project.construction_progress.planned_progress_rate === null ? '미확보' : `${project.construction_progress.planned_progress_rate}%`}</b></div>
                <ChevronRight size={18} />
                <div><span>실제</span><b>{project.construction_progress.actual_progress_rate === null ? '미확보' : `${project.construction_progress.actual_progress_rate}%`}</b></div>
                <span className={`progress-state state-${project.construction_progress.status.toLowerCase()}`}>{progressLabels[project.construction_progress.status]}</span>
              </div>
              {series.length > 0 ? <EChart option={option} className="drawer-chart" /> : <div className="drawer-empty">공정률 데이터 미확보 · 0%로 집계하지 않음</div>}
            </> : <div className="drawer-empty">건설 단계 공정 정보 없음</div>}
          </div>

          <div className="drawer-section">
            <h3><Calendar size={16} /> 공급 · 입주 일정</h3>
            {project.supply_announcements.length ? project.supply_announcements.map(item => <div className="supply-box" key={item.id}><div><b>{item.supply_type}</b><span>{formatUnits(item.supply_units)}</span></div><p>모집 {formatDate(item.application_start_date)} — {formatDate(item.application_end_date)}</p><p>입주 예정 {formatDate(item.planned_move_in_date)}</p></div>) : null}
            {project.schedule_periods.map(item => <div className="supply-box" key={item.id}><div><b>{item.stage === 'MOVE_IN' ? '입주 예정' : '공급 예정'}</b><span>{formatUnits(item.planned_units)}</span></div><p>{item.period_text}{item.period_start_text ? ` · 지정기간 ${item.period_start_text}` : ''}</p></div>)}
            {!project.supply_announcements.length && !project.schedule_periods.length && <div className="drawer-empty">공급·입주 일정 데이터 미확보</div>}
          </div>

          {!project.is_demo && <div className="drawer-section">
            <h3><House size={16} /> 실제 원본 보강 정보</h3>
            {project.project_master_records.length ? project.project_master_records.map((item, index) => <div className="supply-box" key={index}><p>공급예정월 {item.planned_supply_period_text ?? '미확보'}</p><p>입주예정월 {item.planned_move_in_period_text ?? '미확보'}</p><p>건설호수 {formatUnits(item.construction_units)}</p><p>입주지정기간 {item.move_in_period_start_text ?? '미확보'}</p><p>검증 {item.validation_status}</p></div>) : <div className="drawer-empty">원본 보강 정보 미확보</div>}
            {project.lh_notice_candidates.map(item => <div className="supply-box" key={item.pan_id}><p>연결 LH 공고 PAN_ID {item.pan_id}</p><p>{item.pan_name} · {item.project_match_status}</p></div>)}
          </div>}

          <div className="drawer-section source-section">
            <h3><Database size={16} /> 데이터 출처</h3>
            {project.data_sources.map(source => <div className="source-row" key={source.id}><div><b>{source.source_name}</b><small>{source.collection_method} · {source.validation_status}</small></div><ExternalLink size={14} /></div>)}
          </div>
        </>}
      </aside>
    </div>
  )
}
