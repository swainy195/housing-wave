BEGIN;

ALTER TABLE raw_api_records DROP CONSTRAINT IF EXISTS raw_api_records_response_format_check;
ALTER TABLE raw_api_records ADD CONSTRAINT raw_api_records_response_format_check CHECK (response_format IN ('JSON', 'XML', 'HTML_TABLE'));

CREATE TABLE IF NOT EXISTS project_schedule_periods (
    id text PRIMARY KEY,
    project_id text NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    stage text NOT NULL CHECK (stage IN ('POLICY','BUSINESS','PERMIT','CONSTRUCTION','SUPPLY','MOVE_IN')),
    period_text text NOT NULL,
    period_year integer NOT NULL,
    period_month integer NOT NULL CHECK (period_month BETWEEN 1 AND 12),
    planned_units integer CHECK (planned_units IS NULL OR planned_units >= 0),
    source_id text REFERENCES data_sources(id),
    data_status text NOT NULL CHECK (data_status IN ('AVAILABLE','PARTIAL','NOT_CONNECTED','NOT_AVAILABLE')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (project_id, stage, period_text, source_id)
);

CREATE INDEX IF NOT EXISTS idx_project_schedule_periods_month ON project_schedule_periods(period_year, period_month);
DROP TRIGGER IF EXISTS project_schedule_periods_set_updated_at ON project_schedule_periods;
CREATE TRIGGER project_schedule_periods_set_updated_at BEFORE UPDATE ON project_schedule_periods FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMIT;
