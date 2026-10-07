BEGIN;
CREATE TABLE IF NOT EXISTS lh_notice_candidates (
 id text PRIMARY KEY, pan_id text NOT NULL UNIQUE, pan_name text NOT NULL, region_code text, region_name text,
 upper_supply_type text, supply_type text, notice_status text, notice_start_date date, closing_date date, detail_url text,
 raw_record_id text REFERENCES raw_api_records(id), source_id text NOT NULL REFERENCES data_sources(id),
 detail_fetch_status text NOT NULL DEFAULT 'NOT_AVAILABLE' CHECK (detail_fetch_status IN ('NOT_FETCHED','NOT_AVAILABLE','FETCHED','FAILED')),
 detail_fetched_at timestamptz, project_match_status text NOT NULL DEFAULT 'REVIEW_REQUIRED' CHECK (project_match_status IN ('UNMATCHED','MATCHED','REVIEW_REQUIRED')),
 matched_project_id text REFERENCES projects(id), review_reason text NOT NULL, validation_status text NOT NULL CHECK (validation_status IN ('RAW','VALIDATED','REVIEW_REQUIRED','REJECTED')),
 is_demo boolean NOT NULL DEFAULT false, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_lh_notice_candidates_region_status ON lh_notice_candidates(region_name, project_match_status);
DROP TRIGGER IF EXISTS lh_notice_candidates_set_updated_at ON lh_notice_candidates;
CREATE TRIGGER lh_notice_candidates_set_updated_at BEFORE UPDATE ON lh_notice_candidates FOR EACH ROW EXECUTE FUNCTION set_updated_at();
COMMIT;
