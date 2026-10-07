BEGIN;

ALTER TABLE project_candidates ADD COLUMN IF NOT EXISTS source_kind text;
ALTER TABLE project_candidates ADD COLUMN IF NOT EXISTS construction_units integer CHECK (construction_units IS NULL OR construction_units >= 0);
ALTER TABLE project_candidates ADD COLUMN IF NOT EXISTS planned_move_in_period_text text;
ALTER TABLE project_candidates ADD COLUMN IF NOT EXISTS move_in_period_start_text text;
ALTER TABLE project_candidates ADD COLUMN IF NOT EXISTS move_in_period_end_text text;
ALTER TABLE project_candidates ADD COLUMN IF NOT EXISTS match_type text;
ALTER TABLE project_candidates ADD COLUMN IF NOT EXISTS match_evidence jsonb;

ALTER TABLE project_schedule_periods ADD COLUMN IF NOT EXISTS source_record_id text;
ALTER TABLE project_schedule_periods ADD COLUMN IF NOT EXISTS period_granularity text NOT NULL DEFAULT 'MONTH' CHECK (period_granularity IN ('DAY','MONTH','TEXT'));
ALTER TABLE project_schedule_periods ADD COLUMN IF NOT EXISTS period_start_text text;
ALTER TABLE project_schedule_periods ADD COLUMN IF NOT EXISTS period_end_text text;

ALTER TABLE lh_notice_candidates ADD COLUMN IF NOT EXISTS match_type text;
ALTER TABLE lh_notice_candidates ADD COLUMN IF NOT EXISTS match_evidence jsonb;

CREATE INDEX IF NOT EXISTS idx_project_candidates_source_kind ON project_candidates(source_id, source_kind, match_status);

COMMIT;
