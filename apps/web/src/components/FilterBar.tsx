import { RotateCcw, SlidersHorizontal } from 'lucide-react'
import type { DataStatus, ProgressStatus, Stage } from '../types'

export interface Filters {
  region: string
  organization: string
  dataStatus: DataStatus | ''
  progressStatus: ProgressStatus | ''
  stage: Stage | ''
}

export function FilterBar({ filters, onChange, onReset, resultCount }: { filters: Filters; onChange: (filters: Filters) => void; onReset: () => void; resultCount: number }) {
  const update = (key: keyof Filters, value: string) => onChange({ ...filters, [key]: value })
  return (
    <div className="filter-bar">
      <div className="filter-title"><SlidersHorizontal size={16} /><span>사업 필터</span><b>{resultCount}</b></div>
      <label>현재 단계<select value={filters.stage} onChange={e => update('stage', e.target.value)}><option value="">전체</option><option value="BUSINESS">사업화</option><option value="PERMIT">인허가</option><option value="CONSTRUCTION">건설</option><option value="SUPPLY">공급</option><option value="MOVE_IN">입주</option></select></label>
      <label>지역<select value={filters.region} onChange={e => update('region', e.target.value)}><option value="">전체</option><option>서울</option><option>경기</option><option>인천</option></select></label>
      <label>기관<select value={filters.organization} onChange={e => update('organization', e.target.value)}><option value="">전체</option><option>LH</option><option>SH</option><option>GH</option><option>iH</option></select></label>
      <label>데이터 상태<select value={filters.dataStatus} onChange={e => update('dataStatus', e.target.value)}><option value="">전체</option><option value="AVAILABLE">확보</option><option value="PARTIAL">일부확보</option><option value="NOT_CONNECTED">미연계</option><option value="NOT_AVAILABLE">미제공</option></select></label>
      <label>공정 상태<select value={filters.progressStatus} onChange={e => update('progressStatus', e.target.value)}><option value="">전체</option><option value="NORMAL">정상</option><option value="WARNING">주의</option><option value="DELAYED">지연</option><option value="DATA_CHECK">데이터 확인</option></select></label>
      <button className="reset-button" onClick={onReset}><RotateCcw size={14} /> 초기화</button>
    </div>
  )
}
