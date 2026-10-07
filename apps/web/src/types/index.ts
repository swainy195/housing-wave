export type Stage = 'POLICY' | 'BUSINESS' | 'PERMIT' | 'CONSTRUCTION' | 'SUPPLY' | 'MOVE_IN'
export type DataStatus = 'AVAILABLE' | 'PARTIAL' | 'NOT_CONNECTED' | 'NOT_AVAILABLE'
export type ProgressStatus = 'NORMAL' | 'WARNING' | 'DELAYED' | 'DATA_CHECK'

export interface Summary {
  is_demo: boolean
  reference_date: string
  last_updated_at: string
  policy_target_units: number
  linked_units: number
  project_count: number
  delayed_project_count: number
  data_gap_project_count: number
  data_mode: 'DEMO' | 'MIXED' | 'LIVE'
}

export interface PipelineItem {
  stage: Stage
  label: string
  units: number
  project_count: number
  target_ratio: number | null
  data_status: DataStatus
  coverage_rate: number
  is_reference_metric: boolean
}

export interface Progress {
  id: string
  project_id: string
  project_name: string
  organization: string
  region: string
  reference_date: string
  planned_progress_rate: number | null
  actual_progress_rate: number | null
  progress_gap: number | null
  planned_completion_date: string | null
  forecast_completion_date: string | null
  data_status: DataStatus
  status: ProgressStatus
  monthly_series: { month: string; planned: number; actual: number }[]
}

export interface Project {
  id: string
  name: string
  organization: string
  province: string
  district: string
  address: string
  planned_units: number
  housing_type: string
  current_stage: Stage
  data_status: DataStatus
  latitude?: number | null
  longitude?: number | null
  is_demo?: boolean
  is_policy_metric?: boolean
  policy_link_type?: 'OFFICIAL' | 'VERIFIED' | 'CANDIDATE' | null
  progress: Progress | null
}

export interface Alert {
  id: string
  project_id: string
  project_name: string
  organization: string
  region: string
  current_stage: Stage
  issue_type: 'SCHEDULE_DELAY' | 'PROGRESS_DELAY' | 'STALE_DATA' | 'DATA_GAP' | 'SCHEDULE_CHANGED'
  planned_date: string | null
  actual_or_forecast_date: string | null
  delay_days: number | null
  progress_gap: number | null
  data_status: DataStatus
}

export interface Region {
  region: string
  project_count: number
  planned_units: number
  schedule_delay_count: number
  progress_delay_count: number
  data_gap_count: number
  data_status: DataStatus
  note: string
}

export interface UpcomingItem {
  stage: Stage | 'COMPLETION'
  label: string
  project_count: number
  units: number | null
  data_status: DataStatus
  events: { project_id: string; project_name: string; date: string; units: number; data_status: DataStatus }[]
}

export interface Upcoming {
  months: number
  from: string
  to: string
  items: UpcomingItem[]
}

export interface Coverage {
  stages: Stage[]
  organizations: { organization: string; stages: Record<Stage, DataStatus>; note: string }[]
}

export interface ProjectDetail extends Project {
  timeline: {
    id: string
    stage: Stage
    event_type: string
    planned_date: string | null
    actual_date: string | null
    status: string
    delay_days: number | null
    data_status: DataStatus
  }[]
  construction_progress: Progress | null
  supply_announcements: {
    id: string
    supply_type: string
    supply_units: number
    target_group: string
    announcement_date: string
    application_start_date: string
    application_end_date: string
    planned_move_in_date: string
    data_status: DataStatus
  }[]
  schedule_periods: { id: string; stage: Stage; period_text: string; period_start_text: string | null; period_end_text: string | null; planned_units: number | null; data_status: DataStatus }[]
  project_master_records: { source_kind: string | null; planned_supply_period_text: string | null; planned_move_in_period_text: string | null; construction_units: number | null; move_in_period_start_text: string | null; match_type: string | null; validation_status: string }[]
  lh_notice_candidates: { pan_id: string; pan_name: string; project_match_status: string; validation_status: string }[]
  data_sources: {
    id: string
    source_name: string
    collection_method: string
    validation_status: string
    reference_date: string | null
  }[]
}

export interface ReviewCandidateList {
  summary: { review_required: number; matched: number; rejected: number }
  items: { candidate_type: 'LH_NOTICE' | 'LH_MOVE_IN'; candidate_id: string; name: string; province: string; candidate_status: string; validation_status: string; is_demo: boolean; suggestion_count: number }[]
}
export interface ReviewCandidateDetail {
  candidate_type: 'LH_NOTICE' | 'LH_MOVE_IN'
  candidate: { id: string; pan_id?: string; name: string; province: string; district: string | null; block: string | null; address: string | null; units: number | null; housing_type: string | null; candidate_status: string; detail_url?: string | null; planned_move_in_period_text?: string | null }
  suggestions: { id: string; score: number; match_rank: number; review_status: string; review_note: string | null; match_evidence: Record<string, { status: 'MATCH' | 'PARTIAL' | 'MISMATCH' | 'UNKNOWN'; candidate: string | number | null; project: string | number | null; reason: string }>; project_id: string; project_name: string; province: string; district: string; address: string | null; planned_units: number; housing_type: string | null }[]
  retrievals: { project_id: string; project_name: string; search_query: string; search_rank: number; source_url: string; retrieved_at: string }[]
}
