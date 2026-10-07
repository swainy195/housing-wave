BEGIN;
CREATE TABLE IF NOT EXISTS project_candidates (
 id text PRIMARY KEY, source_id text NOT NULL REFERENCES data_sources(id), organization_id text NOT NULL REFERENCES organizations(id),
 source_record_id text, source_row_number integer, project_name_raw text NOT NULL, project_name_normalized text NOT NULL,
 province_raw text, district_raw text, address_raw text, address_normalized text, district_name text, block_name text,
 planned_units integer CHECK (planned_units IS NULL OR planned_units >= 0), housing_type text, supply_type text,
 planned_supply_date date, planned_supply_period_text text, planned_start_date date, planned_completion_date date, planned_move_in_date date,
 source_stage text, normalized_stage text CHECK (normalized_stage IS NULL OR normalized_stage IN ('POLICY','BUSINESS','PERMIT','CONSTRUCTION','SUPPLY','MOVE_IN')),
 external_id text, external_id_type text, match_status text NOT NULL DEFAULT 'REVIEW_REQUIRED' CHECK (match_status IN ('UNMATCHED','MATCHED','REVIEW_REQUIRED','PROMOTED')),
 matched_project_id text REFERENCES projects(id), validation_status text NOT NULL CHECK (validation_status IN ('RAW','VALIDATED','REVIEW_REQUIRED','REJECTED')), review_reason text,
 is_demo boolean NOT NULL DEFAULT false, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE (source_id, source_record_id)
);
CREATE INDEX IF NOT EXISTS idx_project_candidates_org_region ON project_candidates(organization_id, province_raw, match_status);
DROP TRIGGER IF EXISTS project_candidates_set_updated_at ON project_candidates;
CREATE TRIGGER project_candidates_set_updated_at BEFORE UPDATE ON project_candidates FOR EACH ROW EXECUTE FUNCTION set_updated_at();
COMMIT;
