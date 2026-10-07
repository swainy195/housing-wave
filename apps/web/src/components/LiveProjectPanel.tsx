import { Database, ExternalLink } from 'lucide-react'
import { useState } from 'react'
import type { Project } from '../types'
import { formatUnits, stageLabels } from '../utils/format'

export function LiveProjectPanel({ projects, onOpen }: { projects: Project[]; onOpen: (id: string) => void }) {
  const liveProjects = projects.filter(project => !project.is_demo)
  const [showAll, setShowAll] = useState(false)
  if (!liveProjects.length) return null
  return <section className="section live-project-section" aria-labelledby="live-project-title">
    <div className="section-heading compact-heading"><div><div className="eyebrow">VERIFIED SOURCE RECORDS</div><h2 id="live-project-title"><Database size={16} /> 실제 LH 사업 <small>{liveProjects.length}개</small></h2></div><span>공식 좌표 미확보 사업은 지도에 표시하지 않음</span></div>
    <div className="live-project-list">
      {liveProjects.slice(0, showAll ? liveProjects.length : 6).map(project => <button className="live-project-row" key={project.id} onClick={() => onOpen(project.id)}><div><b><small>LIVE</small>{project.name}</b><span>{project.organization} · {project.province} · {project.housing_type ?? '유형 미확보'}</span></div><div><strong>{formatUnits(project.planned_units)}</strong><span>{stageLabels[project.current_stage]}</span></div><ExternalLink size={15} /></button>)}
    </div>
    {liveProjects.length > 6 && <button className="live-project-toggle" onClick={() => setShowAll(value => !value)}>{showAll ? '간단히 보기' : `실제 LH 사업 ${liveProjects.length}개 모두 보기`}</button>}
  </section>
}
