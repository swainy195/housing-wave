import { AlertOctagon, ChevronDown, RefreshCw, Waves } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { AlertsDrawer } from './components/AlertsDrawer'
import { CompactAlerts } from './components/CompactAlerts'
import { ConstructionMonitor } from './components/ConstructionMonitor'
import { CoveragePanel } from './components/CoveragePanel'
import { FilterBar, type Filters } from './components/FilterBar'
import { MetroMap } from './components/MetroMap'
import { LiveProjectPanel } from './components/LiveProjectPanel'
import { Pipeline } from './components/Pipeline'
import { ProjectDrawer } from './components/ProjectDrawer'
import { StatusBadge } from './components/StatusBadge'
import { UpcomingPanel } from './components/UpcomingPanel'
import { ReviewPanel } from './components/ReviewPanel'
import { api } from './services/api'
import type { Alert, Coverage, PipelineItem, Progress, Project, ProjectDetail, Stage, Summary, Upcoming } from './types'
import { formatDate } from './utils/format'

const emptyFilters: Filters = { region: '', organization: '', dataStatus: '', progressStatus: '', stage: '' }
const orderedStages: Stage[] = ['POLICY', 'BUSINESS', 'PERMIT', 'CONSTRUCTION', 'SUPPLY', 'MOVE_IN']
const dataWeight = { AVAILABLE: 1, PARTIAL: .5, NOT_CONNECTED: 0, NOT_AVAILABLE: 0 } as const
const dashboardRetryDelays = [0, 3000, 6000, 10000]

function App() {
  const [summary, setSummary] = useState<Summary | null>(null)
  const [apiPipeline, setApiPipeline] = useState<PipelineItem[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [progress, setProgress] = useState<Progress[]>([])
  const [coverage, setCoverage] = useState<Coverage | null>(null)
  const [upcoming, setUpcoming] = useState<Upcoming | null>(null)
  const [months, setMonths] = useState(3)
  const [filters, setFilters] = useState<Filters>(emptyFilters)
  const [issueFilter, setIssueFilter] = useState('')
  const [detail, setDetail] = useState<ProjectDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [alertsOpen, setAlertsOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [retryAttempt, setRetryAttempt] = useState(0)
  const [error, setError] = useState('')
  const [view, setView] = useState<'dashboard' | 'review'>(() => new URLSearchParams(location.search).get('view') === 'review' ? 'review' : 'dashboard')

  useEffect(() => {
    let cancelled = false
    let retryTimer: number | undefined
    let activeRequest: AbortController | undefined
    const loadDashboard = async () => {
      let lastError = '데이터를 불러오지 못했습니다.'
      for (let attempt = 0; attempt < dashboardRetryDelays.length; attempt += 1) {
        if (cancelled) return
        try {
          activeRequest = new AbortController()
          const { signal } = activeRequest
          const [s, pipeline, projectRows, alertRows, progressRows, coverageRows] = await Promise.all([api.summary(signal), api.pipeline(signal), api.projects(signal), api.alerts(signal), api.progress(signal), api.coverage(signal)])
          if (cancelled) return
          setSummary(s); setApiPipeline(pipeline); setProjects(projectRows); setAlerts(alertRows); setProgress(progressRows); setCoverage(coverageRows)
          setError(''); setRetryAttempt(0); setLoading(false)
          return
        } catch (err) {
          activeRequest?.abort()
          if (cancelled) return
          lastError = err instanceof Error ? err.message : lastError
          if (attempt === dashboardRetryDelays.length - 1) {
            if (!cancelled) { setError(lastError); setLoading(false) }
            return
          }
          if (!cancelled) setRetryAttempt(attempt + 1)
          await new Promise<void>(resolve => { retryTimer = window.setTimeout(resolve, dashboardRetryDelays[attempt + 1]) })
        }
      }
    }
    void loadDashboard()
    return () => { cancelled = true; activeRequest?.abort(); if (retryTimer !== undefined) window.clearTimeout(retryTimer) }
  }, [])
  useEffect(() => {
    if (!summary) return
    let cancelled = false
    api.upcoming(months).then(data => { if (!cancelled) setUpcoming(data) }).catch(() => { if (!cancelled) setUpcoming(null) })
    return () => { cancelled = true }
  }, [months, summary])

  const baseProjects = useMemo(() => projects.filter(project =>
    (!filters.region || project.province === filters.region) &&
    (!filters.organization || project.organization === filters.organization) &&
    (!filters.dataStatus || project.data_status === filters.dataStatus) &&
    (!filters.progressStatus || project.progress?.status === filters.progressStatus)
  ), [projects, filters.region, filters.organization, filters.dataStatus, filters.progressStatus])
  const issueIds = useMemo(() => new Set(alerts.filter(alert => !issueFilter || alert.issue_type === issueFilter).map(alert => alert.project_id)), [alerts, issueFilter])
  const filteredProjects = useMemo(() => baseProjects.filter(project => (!filters.stage || project.current_stage === filters.stage) && (!issueFilter || issueIds.has(project.id))), [baseProjects, filters.stage, issueFilter, issueIds])
  const projectIds = useMemo(() => new Set(filteredProjects.map(project => project.id)), [filteredProjects])
  const contextIds = useMemo(() => new Set(baseProjects.map(project => project.id)), [baseProjects])
  const contextAlerts = useMemo(() => alerts.filter(alert => contextIds.has(alert.project_id)), [alerts, contextIds])
  const filteredProgress = useMemo(() => progress.filter(row => projectIds.has(row.project_id)), [progress, projectIds])

  const pipeline = useMemo(() => {
    const hasContextFilter = Boolean(filters.region || filters.organization || filters.dataStatus || filters.progressStatus)
    if (!hasContextFilter) return apiPipeline
    const metricProjects = baseProjects.filter(project => project.is_policy_metric !== false)
    const target = metricProjects.reduce((sum, project) => sum + project.planned_units, 0)
    return apiPipeline.map((original, index) => {
      const rows = original.stage === 'POLICY' ? metricProjects : metricProjects.filter(project => orderedStages.indexOf(project.current_stage) >= index)
      const units = original.stage === 'POLICY' ? target : rows.reduce((sum, project) => sum + project.planned_units, 0)
      const statuses = rows.map(row => row.data_status)
      const coverageRate = statuses.length ? Math.round(statuses.reduce((sum, status) => sum + dataWeight[status], 0) / statuses.length * 100) : 0
      return { ...original, units, project_count: original.stage === 'POLICY' ? (target ? 1 : 0) : rows.length, target_ratio: target ? Number((units / target * 100).toFixed(1)) : null, coverage_rate: coverageRate, data_status: (coverageRate === 100 ? 'AVAILABLE' : coverageRate ? 'PARTIAL' : 'NOT_AVAILABLE') as PipelineItem['data_status'] }
    })
  }, [apiPipeline, baseProjects, filters.region, filters.organization, filters.dataStatus, filters.progressStatus])

  const filteredUpcoming = useMemo<Upcoming | null>(() => upcoming ? { ...upcoming, items: upcoming.items.map(item => {
    const events = item.events.filter(event => projectIds.has(event.project_id))
    return { ...item, events, project_count: events.length, units: events.length ? events.reduce((sum, event) => sum + event.units, 0) : null }
  }) } : null, [upcoming, projectIds])

  const openProject = async (id: string) => { setDetailLoading(true); setDetail(null); try { setDetail(await api.project(id)) } finally { setDetailLoading(false) } }
  const changeStage = (stage: Stage | null) => setFilters(current => ({ ...current, stage: stage ?? '' }))
  const changeRegion = (region: string) => setFilters(current => ({ ...current, region }))
  const resetFilters = () => { setFilters(emptyFilters); setIssueFilter('') }

  if (loading) return <div className="app-loading"><Waves size={36} /><strong>{retryAttempt ? '서버를 준비하고 있습니다' : '주택파동'}</strong><span>{retryAttempt ? `잠시 후 자동으로 다시 시도합니다. (${dashboardRetryDelays[retryAttempt] / 1000}초 후 · ${retryAttempt + 1}/${dashboardRetryDelays.length})` : '공급 흐름을 연결하고 있습니다'}</span></div>
  if (error || !summary) return <div className="app-error"><AlertOctagon size={36} /><h1>상황판을 불러오지 못했습니다</h1><p>{error}</p><button onClick={() => location.reload()}><RefreshCw size={15} /> 다시 시도</button></div>

  return <div className="app-shell compact-shell">
    <header className="top-header"><div className="brand-block"><div className="brand-icon"><Waves size={22} /></div><div><div className="brand-title">주택파동 <span>HOUSING WAVE</span></div><p>정책에서 입주까지, 주택공급의 흐름을 한눈에</p></div></div><nav aria-label="주 메뉴"><button className={view === 'dashboard' ? 'active' : ''} onClick={() => setView('dashboard')}>통합 상황판</button><button>정책 분석</button><button>사업 목록</button><button className={view === 'review' ? 'active' : ''} onClick={() => setView('review')}>연결 검토</button><button>데이터 관리</button></nav><div className="header-meta"><div><span>기준일</span><b>{formatDate(summary.reference_date)}</b></div><div><span>갱신</span><b>{formatDate(summary.last_updated_at)}</b></div><button className="refresh-button" aria-label="새로고침" onClick={() => location.reload()}><RefreshCw size={16} /></button></div></header>
    <div className={`demo-strip mode-${summary.data_mode.toLowerCase()}`}><b>{summary.data_mode} DATA</b><span>{summary.data_mode === 'DEMO' ? '가상 샘플로 검증 중인 정책 상황판입니다. 실제 정책 통계가 아닙니다.' : summary.data_mode === 'MIXED' ? '실제 데이터와 DEMO 데이터가 함께 표시됩니다.' : '검증된 실제 데이터 모드입니다.'}</span><div className="legend"><StatusBadge status="AVAILABLE" compact /><StatusBadge status="PARTIAL" compact /><StatusBadge status="NOT_CONNECTED" compact /><StatusBadge status="NOT_AVAILABLE" compact /></div></div>
    {view === 'review' ? <ReviewPanel /> : <main>
      <section className="compact-hero"><div><span className="page-kicker">2026 수도권 공급 흐름 · PHASE 1</span><h1>공급은 어디까지 왔고, <em>어디에서 멈춰 있나</em></h1></div><div className="hero-statline"><span>정책 목표 <b>{summary.policy_target_units.toLocaleString()}호</b></span><i /><span>검증 연결 <b>{summary.linked_units.toLocaleString()}호</b></span><i /><span className="warn">점검 <b>{contextAlerts.length}건</b></span></div></section>
      <FilterBar filters={filters} onChange={setFilters} onReset={resetFilters} resultCount={filteredProjects.length} />
      <Pipeline items={pipeline} selectedStage={filters.stage || null} onSelect={changeStage} />
      <LiveProjectPanel projects={filteredProjects} onOpen={openProject} />
      <div className="dashboard-row map-alert-row"><MetroMap projects={filteredProjects} selectedRegion={filters.region} onRegion={changeRegion} onOpen={openProject} /><CompactAlerts alerts={contextAlerts} activeIssue={issueFilter} onIssue={setIssueFilter} onOpen={openProject} onAll={() => setAlertsOpen(true)} /></div>
      <div className="dashboard-row progress-upcoming-row"><ConstructionMonitor rows={filteredProgress} onOpen={openProject} /><UpcomingPanel data={filteredUpcoming} months={months} onMonthsChange={setMonths} onOpen={openProject} /></div>
      {coverage && <CoveragePanel coverage={coverage} />}
    </main>}
    <footer><div><Waves size={16} /><b>주택파동</b><span>Phase 1 PoC</span></div><p>출처 · 기준일 · 수집방법 · 검증상태를 함께 기록합니다.</p><button>데이터 정책 <ChevronDown size={13} /></button></footer>
    <ProjectDrawer project={detail} loading={detailLoading} onClose={() => { setDetail(null); setDetailLoading(false) }} />
    <AlertsDrawer open={alertsOpen} alerts={contextAlerts} onClose={() => setAlertsOpen(false)} onOpen={(id) => { setAlertsOpen(false); openProject(id) }} />
  </div>
}
export default App
