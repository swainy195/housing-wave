BEGIN;

CREATE TABLE IF NOT EXISTS raw_api_records (
    id text PRIMARY KEY,
    source_id text NOT NULL REFERENCES data_sources(id),
    source_system text NOT NULL,
    endpoint_name text NOT NULL,
    request_key text NOT NULL,
    request_params jsonb NOT NULL DEFAULT '{}'::jsonb,
    raw_payload jsonb NOT NULL,
    response_format text NOT NULL CHECK (response_format IN ('JSON', 'XML')),
    fetched_at timestamptz NOT NULL,
    reference_date date,
    http_status integer NOT NULL,
    parse_status text NOT NULL CHECK (parse_status IN ('PARSED', 'REVIEW_REQUIRED', 'REJECTED')),
    checksum text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (source_id, checksum)
);

CREATE TABLE IF NOT EXISTS external_identifiers (
    entity_type text NOT NULL CHECK (entity_type IN ('PROJECT', 'PROJECT_EVENT')),
    entity_id text NOT NULL,
    source_system text NOT NULL,
    external_id text NOT NULL,
    raw_record_id text REFERENCES raw_api_records(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (entity_type, source_system, external_id),
    UNIQUE (entity_type, entity_id, source_system)
);

CREATE INDEX IF NOT EXISTS idx_raw_api_records_source_fetched ON raw_api_records(source_id, fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_external_identifiers_entity ON external_identifiers(entity_type, entity_id);

COMMIT;
