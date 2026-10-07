BEGIN;

CREATE TABLE IF NOT EXISTS candidate_match_suggestions (
  id text PRIMARY KEY,
  candidate_type text NOT NULL CHECK (candidate_type IN ('LH_NOTICE', 'LH_MOVE_IN')),
  candidate_id text NOT NULL,
  project_id text NOT NULL REFERENCES projects(id),
  score numeric(6,2) NOT NULL CHECK (score >= 0),
  match_rank integer NOT NULL CHECK (match_rank BETWEEN 1 AND 3),
  match_evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
  review_status text NOT NULL DEFAULT 'PENDING' CHECK (review_status IN ('PENDING', 'VERIFIED', 'REJECTED')),
  reviewed_by text,
  reviewed_at timestamptz,
  review_note text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (candidate_type, candidate_id, project_id)
);

CREATE INDEX IF NOT EXISTS idx_match_suggestions_candidate ON candidate_match_suggestions(candidate_type, candidate_id, match_rank);
CREATE INDEX IF NOT EXISTS idx_match_suggestions_review ON candidate_match_suggestions(review_status, candidate_type);

CREATE TABLE IF NOT EXISTS candidate_match_reviews (
  id text PRIMARY KEY,
  suggestion_id text NOT NULL REFERENCES candidate_match_suggestions(id),
  candidate_type text NOT NULL CHECK (candidate_type IN ('LH_NOTICE', 'LH_MOVE_IN')),
  candidate_id text NOT NULL,
  project_id text NOT NULL REFERENCES projects(id),
  decision text NOT NULL CHECK (decision IN ('VERIFIED', 'REJECTED')),
  reviewed_by text NOT NULL DEFAULT 'LOCAL_REVIEWER',
  reviewed_at timestamptz NOT NULL DEFAULT now(),
  review_note text,
  match_evidence_snapshot jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_match_reviews_candidate ON candidate_match_reviews(candidate_type, candidate_id, reviewed_at DESC);

COMMIT;
