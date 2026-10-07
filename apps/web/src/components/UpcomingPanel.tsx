import { ArrowRight, CalendarDays } from 'lucide-react'
import type { Upcoming } from '../types'
import { formatDate, formatUnits } from '../utils/format'

export function UpcomingPanel({ data, months, onMonthsChange, onOpen }: { data: Upcoming | null; months: number; onMonthsChange: (months: number) => void; onOpen: (id: string) => void }) {
  return (
    <section className="section upcoming-section" aria-labelledby="upcoming-title">
      <div className="section-heading upcoming-heading">
        <div><div className="eyebrow">FORWARD LOOK</div><h2 id="upcoming-title">향후 일정</h2></div>
        <div className="period-tabs" role="tablist" aria-label="향후 일정 기간">
          {[3, 6, 12].map(value => <button key={value} role="tab" aria-selected={months === value} className={months === value ? 'active' : ''} onClick={() => onMonthsChange(value)}>{value}개월</button>)}
        </div>
      </div>
      <div className="upcoming-window"><CalendarDays size={14} /> {formatDate(data?.from)} — {formatDate(data?.to)}</div>
      <div className="upcoming-grid compact-upcoming-grid">
        {data?.items.map(item => (
          <div className="upcoming-item" key={item.stage}>
            <div className="upcoming-stage">{item.label}<span>{item.project_count}개 사업</span></div>
            <strong>{formatUnits(item.units)}</strong>
            {item.events.length ? (
              <button className="next-event" onClick={() => onOpen(item.events[0].project_id)}><span><small>가장 가까운 일정</small>{item.events[0].project_name}</span><b>{formatDate(item.events[0].date)} <ArrowRight size={13} /></b></button>
            ) : <div className="no-event">데이터 미확보</div>}
          </div>
        ))}
      </div>
    </section>
  )
}
