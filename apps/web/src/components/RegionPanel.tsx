import { Building2, CircleAlert, MapPinned } from 'lucide-react'
import type { Region } from '../types'
import { formatUnits } from '../utils/format'
import { StatusBadge } from './StatusBadge'

export function RegionPanel({ regions, selected, onSelect }: { regions: Region[]; selected: string; onSelect: (region: string) => void }) {
  return (
    <section className="section region-section" aria-labelledby="region-title">
      <div className="section-heading">
        <div><div className="eyebrow">REGIONAL VIEW</div><h2 id="region-title">지역 · 기관 상황</h2></div>
        <span className="section-subtitle"><MapPinned size={15} /> 지도 연계 준비 영역</span>
      </div>
      <div className="region-grid">
        {regions.map(region => (
          <button key={region.region} className={`region-card ${selected === region.region ? 'selected' : ''}`} onClick={() => onSelect(selected === region.region ? '' : region.region)}>
            <div className="region-card-head"><span>{region.region}</span><StatusBadge status={region.data_status} compact /></div>
            <div className="region-primary"><strong>{formatUnits(region.planned_units)}</strong><small>{region.project_count}개 사업</small></div>
            <div className="region-stats">
              <span><CircleAlert size={13} /> 일정지연 <b>{region.schedule_delay_count}</b></span>
              <span><Building2 size={13} /> 공정지연 <b>{region.progress_delay_count}</b></span>
              <span>데이터공백 <b>{region.data_gap_count}</b></span>
            </div>
            <p>{region.note}</p>
          </button>
        ))}
      </div>
    </section>
  )
}

