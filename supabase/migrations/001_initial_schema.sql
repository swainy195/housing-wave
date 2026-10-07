BEGIN;

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS organizations (
    id text PRIMARY KEY,
    name text NOT NULL UNIQUE,
    organization_type text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS policies (
    id text PRIMARY KEY,
    name text NOT NULL,
    organization_id text NOT NULL REFERENCES organizations(id),
    announced_date date,
    target_units integer NOT NULL CHECK (target_units >= 0),
    target_stage text NOT NULL CHECK (target_stage IN ('POLICY','BUSINESS','PERMIT','CONSTRUCTION','SUPPLY','MOVE_IN')),
    target_region text,
    target_date date,
    source_url text,
    data_status text NOT NULL CHECK (data_status IN ('AVAILABLE','PARTIAL','NOT_CONNECTED','NOT_AVAILABLE')),
    is_demo boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS projects (
    id text PRIMARY KEY,
    name text NOT NULL,
    organization_id text NOT NULL REFERENCES organizations(id),
    province text NOT NULL,
    district text,
    address text,
    latitude double precision,
    longitude double precision,
    location geometry(Point, 4326),
    planned_units integer NOT NULL CHECK (planned_units >= 0),
    housing_type text,
    current_stage text NOT NULL CHECK (current_stage IN ('POLICY','BUSINESS','PERMIT','CONSTRUCTION','SUPPLY','MOVE_IN')),
    data_status text NOT NULL CHECK (data_status IN ('AVAILABLE','PARTIAL','NOT_CONNECTED','NOT_AVAILABLE')),
    is_demo boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK ((latitude IS NULL AND longitude IS NULL) OR (latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180))
);

CREATE TABLE IF NOT EXISTS policy_project_links (
    id text PRIMARY KEY,
    policy_id text NOT NULL REFERENCES policies(id) ON DELETE CASCADE,
    project_id text NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    link_type text NOT NULL CHECK (link_type IN ('OFFICIAL','VERIFIED','CANDIDATE')),
    evidence_url text,
    evidence_text text,
    verified_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (policy_id, project_id)
);

CREATE TABLE IF NOT EXISTS data_sources (
    id text PRIMARY KEY,
    organization_id text NOT NULL REFERENCES organizations(id),
    source_name text NOT NULL,
    source_url text,
    source_type text NOT NULL CHECK (source_type IN ('API','WEB','EXCEL','CSV','PDF','HWP','MANUAL','DEMO')),
    collection_method text NOT NULL,
    reference_date date,
    collected_at timestamptz,
    validation_status text NOT NULL CHECK (validation_status IN ('RAW','VALIDATED','REVIEW_REQUIRED','REJECTED','DEMO_ONLY','PENDING')),
    is_demo boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS project_events (
    id text PRIMARY KEY,
    project_id text NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    stage text NOT NULL CHECK (stage IN ('POLICY','BUSINESS','PERMIT','CONSTRUCTION','SUPPLY','MOVE_IN')),
    event_type text NOT NULL,
    planned_date date,
    actual_date date,
    status text NOT NULL,
    reference_date date NOT NULL,
    source_id text REFERENCES data_sources(id),
    data_status text NOT NULL CHECK (data_status IN ('AVAILABLE','PARTIAL','NOT_CONNECTED','NOT_AVAILABLE')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS construction_progress (
    id text PRIMARY KEY,
    project_id text NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    reference_date date NOT NULL,
    planned_progress_rate numeric(5,2),
    actual_progress_rate numeric(5,2),
    planned_completion_date date,
    forecast_completion_date date,
    source_id text REFERENCES data_sources(id),
    data_status text NOT NULL CHECK (data_status IN ('AVAILABLE','PARTIAL','NOT_CONNECTED','NOT_AVAILABLE')),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (project_id, reference_date),
    CHECK (planned_progress_rate IS NULL OR planned_progress_rate BETWEEN 0 AND 100),
    CHECK (actual_progress_rate IS NULL OR actual_progress_rate BETWEEN 0 AND 100)
);

CREATE TABLE IF NOT EXISTS supply_announcements (
    id text PRIMARY KEY,
    project_id text NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    supply_type text NOT NULL,
    supply_units integer CHECK (supply_units >= 0),
    target_group text,
    announcement_date date,
    application_start_date date,
    application_end_date date,
    planned_move_in_date date,
    source_id text REFERENCES data_sources(id),
    data_status text NOT NULL CHECK (data_status IN ('AVAILABLE','PARTIAL','NOT_CONNECTED','NOT_AVAILABLE')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS data_status_history (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity_type text NOT NULL,
    entity_id text NOT NULL,
    previous_status text CHECK (previous_status IS NULL OR previous_status IN ('AVAILABLE','PARTIAL','NOT_CONNECTED','NOT_AVAILABLE')),
    new_status text NOT NULL CHECK (new_status IN ('AVAILABLE','PARTIAL','NOT_CONNECTED','NOT_AVAILABLE')),
    changed_at timestamptz NOT NULL DEFAULT now(),
    reason text
);

CREATE TABLE IF NOT EXISTS organization_stage_coverage (
    organization_id text NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    stage text NOT NULL CHECK (stage IN ('POLICY','BUSINESS','PERMIT','CONSTRUCTION','SUPPLY','MOVE_IN')),
    data_status text NOT NULL CHECK (data_status IN ('AVAILABLE','PARTIAL','NOT_CONNECTED','NOT_AVAILABLE')),
    note text,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (organization_id, stage)
);

CREATE INDEX IF NOT EXISTS idx_projects_location ON projects USING gist(location);
CREATE INDEX IF NOT EXISTS idx_projects_region_stage ON projects(province, current_stage);
CREATE INDEX IF NOT EXISTS idx_project_events_project_date ON project_events(project_id, reference_date DESC);
CREATE INDEX IF NOT EXISTS idx_construction_progress_project_date ON construction_progress(project_id, reference_date DESC);
CREATE INDEX IF NOT EXISTS idx_supply_announcements_dates ON supply_announcements(announcement_date, planned_move_in_date);
CREATE INDEX IF NOT EXISTS idx_data_status_history_entity ON data_status_history(entity_type, entity_id, changed_at DESC);

CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS organizations_set_updated_at ON organizations;
CREATE TRIGGER organizations_set_updated_at BEFORE UPDATE ON organizations FOR EACH ROW EXECUTE FUNCTION set_updated_at();
DROP TRIGGER IF EXISTS policies_set_updated_at ON policies;
CREATE TRIGGER policies_set_updated_at BEFORE UPDATE ON policies FOR EACH ROW EXECUTE FUNCTION set_updated_at();
DROP TRIGGER IF EXISTS projects_set_updated_at ON projects;
CREATE TRIGGER projects_set_updated_at BEFORE UPDATE ON projects FOR EACH ROW EXECUTE FUNCTION set_updated_at();
DROP TRIGGER IF EXISTS project_events_set_updated_at ON project_events;
CREATE TRIGGER project_events_set_updated_at BEFORE UPDATE ON project_events FOR EACH ROW EXECUTE FUNCTION set_updated_at();
DROP TRIGGER IF EXISTS supply_announcements_set_updated_at ON supply_announcements;
CREATE TRIGGER supply_announcements_set_updated_at BEFORE UPDATE ON supply_announcements FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE FUNCTION sync_project_location() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.latitude IS NULL OR NEW.longitude IS NULL THEN
        NEW.location = NULL;
    ELSE
        NEW.location = ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326);
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS projects_sync_location ON projects;
CREATE TRIGGER projects_sync_location BEFORE INSERT OR UPDATE OF latitude, longitude ON projects FOR EACH ROW EXECUTE FUNCTION sync_project_location();

CREATE OR REPLACE VIEW v_latest_construction_progress AS
SELECT id, project_id, reference_date, planned_progress_rate, actual_progress_rate,
       CASE WHEN planned_progress_rate IS NULL OR actual_progress_rate IS NULL THEN NULL
            ELSE actual_progress_rate - planned_progress_rate END AS progress_gap,
       planned_completion_date, forecast_completion_date, source_id, data_status, created_at
FROM (
    SELECT cp.*, ROW_NUMBER() OVER (PARTITION BY project_id ORDER BY reference_date DESC, created_at DESC) AS row_num
    FROM construction_progress cp
) ranked
WHERE row_num = 1;

CREATE OR REPLACE VIEW v_project_current_status AS
SELECT p.*, lcp.reference_date AS progress_reference_date,
       lcp.planned_progress_rate, lcp.actual_progress_rate, lcp.progress_gap,
       lcp.planned_completion_date, lcp.forecast_completion_date
FROM projects p
LEFT JOIN v_latest_construction_progress lcp ON lcp.project_id = p.id;

CREATE OR REPLACE VIEW v_policy_progress AS
SELECT pol.id AS policy_id, pol.name AS policy_name, pol.target_units, pol.target_stage,
       COALESCE(SUM(p.planned_units) FILTER (WHERE ppl.link_type IN ('OFFICIAL','VERIFIED')), 0) AS business_units,
       COALESCE(SUM(p.planned_units) FILTER (WHERE ppl.link_type IN ('OFFICIAL','VERIFIED') AND p.current_stage IN ('PERMIT','CONSTRUCTION','SUPPLY','MOVE_IN')), 0) AS permit_units,
       COALESCE(SUM(p.planned_units) FILTER (WHERE ppl.link_type IN ('OFFICIAL','VERIFIED') AND p.current_stage IN ('CONSTRUCTION','SUPPLY','MOVE_IN')), 0) AS construction_units,
       COALESCE(SUM(p.planned_units) FILTER (WHERE ppl.link_type IN ('OFFICIAL','VERIFIED') AND p.current_stage IN ('SUPPLY','MOVE_IN')), 0) AS supply_units,
       COALESCE(SUM(p.planned_units) FILTER (WHERE ppl.link_type IN ('OFFICIAL','VERIFIED') AND p.current_stage = 'MOVE_IN'), 0) AS move_in_units
FROM policies pol
LEFT JOIN policy_project_links ppl ON ppl.policy_id = pol.id
LEFT JOIN projects p ON p.id = ppl.project_id
GROUP BY pol.id, pol.name, pol.target_units, pol.target_stage;

CREATE OR REPLACE VIEW v_data_coverage AS
SELECT o.name AS organization, osc.stage,
       CASE osc.stage WHEN 'POLICY' THEN 1 WHEN 'BUSINESS' THEN 2 WHEN 'PERMIT' THEN 3 WHEN 'CONSTRUCTION' THEN 4 WHEN 'SUPPLY' THEN 5 ELSE 6 END AS stage_order,
       osc.data_status, osc.note
FROM organization_stage_coverage osc
JOIN organizations o ON o.id = osc.organization_id;

CREATE OR REPLACE VIEW v_upcoming_events AS
SELECT pe.id, pe.project_id, pe.stage, pe.event_type,
       COALESCE(pe.actual_date, pe.planned_date) AS event_date,
       p.planned_units, pe.data_status, pe.source_id
FROM project_events pe
JOIN projects p ON p.id = pe.project_id
WHERE COALESCE(pe.actual_date, pe.planned_date) IS NOT NULL;

COMMIT;
