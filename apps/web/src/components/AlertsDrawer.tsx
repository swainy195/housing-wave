import { AlertTriangle, X } from 'lucide-react'
import type { Alert } from '../types'
import { issueLabels, stageLabels } from '../utils/format'
import { StatusBadge } from './StatusBadge'

export function AlertsDrawer({ open, alerts, onClose, onOpen }: { open: boolean; alerts: Alert[]; onClose: () => void; onOpen: (id: string) => void }) {
  return <div className={`alerts-drawer-shell ${open ? 'open' : ''}`} aria-hidden={!open}>
    <button className="drawer-backdrop" onClick={onClose} aria-label="점검 목록 닫기" />
    <aside className="alerts-drawer" aria-label="전체 점검 목록"><div className="alerts-drawer-header"><div><div className="eyebrow warning">ALL ALERTS</div><h2><AlertTriangle size={18} /> 전체 점검 대상 <b>{alerts.length}</b></h2></div><button className="drawer-close" onClick={onClose}><X size={20} /></button></div>
      <div className="all-alert-list">{alerts.map(alert => <button key={alert.id} onClick={() => onOpen(alert.project_id)}><div><span className={`issue issue-${alert.issue_type.toLowerCase()}`}>{issueLabels[alert.issue_type]}</span><strong>{alert.project_name}</strong><small>{alert.organization} · {alert.region} · {stageLabels[alert.current_stage]}</small></div><div><b className={alert.progress_gap !== null || alert.delay_days ? 'negative' : ''}>{alert.progress_gap !== null ? `${alert.progress_gap}%p` : alert.delay_days ? `+${alert.delay_days}일` : '—'}</b><StatusBadge status={alert.data_status} compact /></div></button>)}</div>
    </aside>
  </div>
}
