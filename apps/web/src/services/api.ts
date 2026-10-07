import type { Alert, Coverage, PipelineItem, Progress, Project, ProjectDetail, Region, Summary, Upcoming, ReviewCandidateList, ReviewCandidateDetail } from '../types'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`)
  if (!response.ok) throw new Error(`API 요청 실패 (${response.status})`)
  return response.json() as Promise<T>
}
async function post<T>(path: string, body: unknown = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  if (!response.ok) throw new Error(`API 요청 실패 (${response.status})`)
  return response.json() as Promise<T>
}

export const api = {
  summary: () => get<Summary>('/api/dashboard/summary'),
  pipeline: () => get<PipelineItem[]>('/api/dashboard/pipeline'),
  coverage: () => get<Coverage>('/api/dashboard/data-coverage'),
  projects: () => get<Project[]>('/api/projects'),
  project: (id: string) => get<ProjectDetail>(`/api/projects/${id}`),
  progress: () => get<Progress[]>('/api/construction/progress'),
  alerts: () => get<Alert[]>('/api/alerts'),
  upcoming: (months: number) => get<Upcoming>(`/api/upcoming?months=${months}`),
  regions: () => get<Region[]>('/api/regions'),
  reviewCandidates: () => get<ReviewCandidateList>('/api/review/candidates'),
  reviewCandidate: (kind: string, id: string) => get<ReviewCandidateDetail>(`/api/review/candidates/${kind}/${id}`),
  rebuildSuggestions: () => post('/api/review/rebuild-suggestions'),
  verifySuggestion: (id: string, review_note?: string) => post(`/api/review/suggestions/${id}/verify`, { review_note }),
  rejectSuggestion: (id: string, review_note?: string) => post(`/api/review/suggestions/${id}/reject`, { review_note }),
}
