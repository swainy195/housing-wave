import { AlertTriangle, ArrowUpRight, DatabaseZap } from 'lucide-react'
import type { Alert } from '../types'
import { formatDate, issueLabels, stageLabels } from '../utils/format'
import { StatusBadge } from './StatusBadge'

export function AlertsTable({ alerts, onOpen }: { alerts: Alert[]; onOpen: (id: string) => void }) {
  return (
    <section className="section alert-section" aria-labelledby="alert-title">
      <div className="section-heading">
        <div><div className="eyebrow warning">ATTENTION</div><h2 id="alert-title">병목 · 주요 점검 대상</h2></div>
        <span className="section-count"><AlertTriangle size={15} /> {alerts.length}건 점검 필요</span>
      </div>
      <div className="table-scroll">
        <table className="data-table">
          <thead><tr><th>사업명</th><th>기관 / 지역</th><th>현재 단계</th><th>문제 유형</th><th>계획일</th><th>예정일</th><th>차이</th><th>데이터</th><th /></tr></thead>
          <tbody>
            {alerts.slice(0, 8).map(alert => (
              <tr key={alert.id} onClick={() => onOpen(alert.project_id)}>
                <td><strong>{alert.project_name}</strong></td>
                <td><span className="org-mark">{alert.organization}</span><small>{alert.region}</small></td>
                <td><span className="stage-chip">{stageLabels[alert.current_stage]}</span></td>
                <td><span className={`issue issue-${alert.issue_type.toLowerCase()}`}>{alert.issue_type === 'DATA_GAP' ? <DatabaseZap size={13} /> : <AlertTriangle size={13} />}{issueLabels[alert.issue_type]}</span></td>
                <td>{formatDate(alert.planned_date)}</td>
                <td>{formatDate(alert.actual_or_forecast_date)}</td>
                <td className={alert.progress_gap !== null || alert.delay_days ? 'negative' : ''}>{alert.progress_gap !== null ? `${alert.progress_gap}%p` : alert.delay_days ? `+${alert.delay_days}일` : '—'}</td>
                <td><StatusBadge status={alert.data_status} compact /></td>
                <td><button className="row-open" aria-label={`${alert.project_name} 상세 보기`}><ArrowUpRight size={16} /></button></td>
              </tr>
            ))}
          </tbody>
        </table>
        {!alerts.length && <div className="empty-state">선택한 조건의 점검 대상이 없습니다.</div>}
      </div>
    </section>
  )
}

