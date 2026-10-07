import { AlertTriangle, ArrowUpRight, CalendarClock, DatabaseZap, ListFilter } from 'lucide-react'
import type { Alert } from '../types'
import { issueLabels } from '../utils/format'

const categories = [
  { key: 'SCHEDULE_DELAY', label: '일정지연' },
  { key: 'PROGRESS_DELAY', label: '공정지연' },
  { key: 'DATA_GAP', label: '데이터공백' },
  { key: 'SCHEDULE_CHANGED', label: '일정변경' },
]

export function CompactAlerts({ alerts, activeIssue, onIssue, onOpen, onAll }: { alerts: Alert[]; activeIssue: string; onIssue: (issue: string) => void; onOpen: (id: string) => void; onAll: () => void }) {
  const visible = (activeIssue ? alerts.filter(alert => alert.issue_type === activeIssue) : alerts).slice(0, 5)
  return (
    <section className="section compact-alerts" aria-labelledby="compact-alert-title">
      <div className="section-heading compact-heading"><div><div className="eyebrow warning">ATTENTION</div><h2 id="compact-alert-title">주요 점검 대상</h2></div><button className="outline-action" onClick={onAll}><ListFilter size={14} /> 전체 보기</button></div>
      <div className="alert-totals">
        {categories.map(category => {
          const count = alerts.filter(alert => alert.issue_type === category.key).length
          return <button key={category.key} className={activeIssue === category.key ? 'active' : ''} onClick={() => onIssue(activeIssue === category.key ? '' : category.key)}><span>{category.label}</span><b>{count}</b></button>
        })}
      </div>
      <div className="alert-list">
        {visible.map(alert => <button className="compact-alert-row" key={alert.id} onClick={() => onOpen(alert.project_id)}>
          <span className={`alert-icon ${alert.issue_type.toLowerCase()}`}>{alert.issue_type === 'DATA_GAP' ? <DatabaseZap size={15} /> : alert.issue_type === 'SCHEDULE_CHANGED' ? <CalendarClock size={15} /> : <AlertTriangle size={15} />}</span>
          <div><strong>{alert.project_name}</strong><small>{alert.organization} · {alert.region} · {issueLabels[alert.issue_type]}</small></div>
          <em>{alert.progress_gap !== null ? `${alert.progress_gap}%p` : alert.delay_days ? `+${alert.delay_days}일` : '미확보'}</em><ArrowUpRight size={15} />
        </button>)}
        {!visible.length && <div className="compact-empty">선택한 조건의 점검 대상이 없습니다.</div>}
      </div>
    </section>
  )
}

