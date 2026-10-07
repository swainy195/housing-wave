import { ChevronDown, Database, Info, Link2Off, MinusCircle, RefreshCw } from 'lucide-react'
import { useState } from 'react'
import type { Coverage, Stage } from '../types'
import { stageLabels } from '../utils/format'
import { StatusBadge } from './StatusBadge'

export function CoveragePanel({ coverage }: { coverage: Coverage }) {
  const [expanded, setExpanded] = useState(false)
  const statuses = coverage.organizations.flatMap(row => Object.values(row.stages))
  const availableRate = Math.round(statuses.reduce((sum, status) => sum + (status === 'AVAILABLE' ? 1 : status === 'PARTIAL' ? .5 : 0), 0) / statuses.length * 100)
  const notConnected = statuses.filter(status => status === 'NOT_CONNECTED').length
  const notAvailable = statuses.filter(status => status === 'NOT_AVAILABLE').length
  return <section className={`section compact-coverage ${expanded ? 'expanded' : ''}`} aria-labelledby="coverage-title">
    <div className="coverage-summary">
      <div className="coverage-title"><div className="eyebrow gap">DATA GAPS</div><h2 id="coverage-title"><Database size={16} /> 데이터 커버리지</h2></div>
      <div className="coverage-metrics"><div><span>데이터 확보율</span><strong>{availableRate}%</strong></div><div><Link2Off size={14} /><span>미연계</span><strong>{notConnected}</strong></div><div><MinusCircle size={14} /><span>미제공</span><strong>{notAvailable}</strong></div><div><RefreshCw size={14} /><span>갱신지연</span><strong>0</strong></div></div>
      <button className="outline-action" onClick={() => setExpanded(value => !value)}>{expanded ? '접기' : '상세 보기'} <ChevronDown size={15} className={expanded ? 'turned' : ''} /></button>
    </div>
    {expanded && <div className="coverage-table-wrap"><table className="coverage-table"><thead><tr><th>기관</th>{coverage.stages.map(stage => <th key={stage}>{stageLabels[stage as Stage]}</th>)}<th>비고</th></tr></thead><tbody>{coverage.organizations.map(row => <tr key={row.organization}><td><span className="org-logo">{row.organization}</span></td>{coverage.stages.map(stage => <td key={stage}><StatusBadge status={row.stages[stage as Stage]} compact /></td>)}<td className="coverage-note">{row.organization === 'SH' && <Info size={13} />}{row.note}</td></tr>)}</tbody></table></div>}
  </section>
}
