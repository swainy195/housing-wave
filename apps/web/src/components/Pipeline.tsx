import { ArrowRight, CheckCircle2 } from 'lucide-react'
import type { PipelineItem, Stage } from '../types'
import { formatUnits } from '../utils/format'
import { StatusBadge } from './StatusBadge'

export function Pipeline({ items, selectedStage, onSelect }: { items: PipelineItem[]; selectedStage: Stage | null; onSelect: (stage: Stage | null) => void }) {
  return (
    <section className="section pipeline-section" aria-labelledby="pipeline-title">
      <div className="section-heading pipeline-heading">
        <div>
          <div className="eyebrow">SUPPLY LIFECYCLE</div>
          <h2 id="pipeline-title">6단계 공급 생애주기</h2>
        </div>
        <div className="pipeline-help"><CheckCircle2 size={15} /> OFFICIAL·VERIFIED 연결 사업만 집계</div>
      </div>
      <div className="pipeline-grid">
        {items.map((item, index) => (
          <div className="pipeline-node-wrap" key={item.stage}>
            <button
              className={`pipeline-node ${selectedStage === item.stage ? 'selected' : ''}`}
              onClick={() => onSelect(selectedStage === item.stage ? null : item.stage)}
              aria-pressed={selectedStage === item.stage}
            >
              <div className="pipeline-topline">
                <span className="stage-index">{String(index + 1).padStart(2, '0')}</span>
                <StatusBadge status={item.data_status} compact />
              </div>
              <div className="stage-name">{item.label}</div>
              <div className="stage-units">{formatUnits(item.units)}</div>
              <div className="stage-meta"><span>{item.project_count}개 {item.stage === 'POLICY' ? '정책' : '사업'}</span><strong>{item.target_ratio?.toFixed(1)}%</strong></div>
              <div className="coverage-track"><span style={{ width: `${item.coverage_rate}%` }} /></div>
              <div className="coverage-label"><span>데이터 확보율</span><b>{item.coverage_rate}%</b></div>
            </button>
            {index < items.length - 1 && <ArrowRight className="pipeline-arrow" size={18} aria-hidden="true" />}
          </div>
        ))}
      </div>
      {selectedStage && <button className="selection-note" onClick={() => onSelect(null)}>‘{items.find(i => i.stage === selectedStage)?.label}’ 단계 필터 적용 중 · 해제</button>}
    </section>
  )
}

