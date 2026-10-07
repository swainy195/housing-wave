BEGIN;

CREATE TABLE IF NOT EXISTS project_notice_retrievals (
  id text PRIMARY KEY,
  project_id text NOT NULL REFERENCES projects(id),
  candidate_id text NOT NULL REFERENCES lh_notice_candidates(id),
  search_query text NOT NULL,
  search_rank integer NOT NULL,
  source_url text NOT NULL,
  retrieved_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, candidate_id, search_query)
);
CREATE INDEX IF NOT EXISTS idx_project_notice_retrievals_candidate ON project_notice_retrievals(candidate_id, project_id);

COMMIT;
