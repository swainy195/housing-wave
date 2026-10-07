BEGIN;

CREATE TABLE IF NOT EXISTS housing_complex_references (
    id text PRIMARY KEY,
    source_id text NOT NULL REFERENCES data_sources(id),
    raw_record_id text REFERENCES raw_api_records(id),
    source_record_id text NOT NULL,
    district text,
    complex_name text NOT NULL,
    complex_name_normalized text NOT NULL,
    housing_type text,
    total_households integer CHECK (total_households IS NULL OR total_households >= 0),
    move_in_start_date date,
    move_in_start_raw text,
    address_raw text,
    postal_code text,
    phone text,
    validation_status text NOT NULL CHECK (validation_status IN ('RAW','VALIDATED','REVIEW_REQUIRED','REJECTED')),
    is_demo boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (source_id, source_record_id)
);

CREATE TABLE IF NOT EXISTS project_housing_complex_references (
    project_id text NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    reference_id text NOT NULL REFERENCES housing_complex_references(id) ON DELETE CASCADE,
    match_type text NOT NULL CHECK (match_type = 'EXACT_NAME_DISTRICT'),
    match_evidence jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (project_id, reference_id)
);

CREATE INDEX IF NOT EXISTS idx_housing_complex_references_name_district
    ON housing_complex_references(complex_name_normalized, district);
CREATE INDEX IF NOT EXISTS idx_housing_complex_references_source
    ON housing_complex_references(source_id, source_record_id);

DROP TRIGGER IF EXISTS housing_complex_references_set_updated_at ON housing_complex_references;
CREATE TRIGGER housing_complex_references_set_updated_at
    BEFORE UPDATE ON housing_complex_references
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMIT;
