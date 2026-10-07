BEGIN;

ALTER TABLE raw_api_records DROP CONSTRAINT IF EXISTS raw_api_records_response_format_check;
ALTER TABLE raw_api_records ADD CONSTRAINT raw_api_records_response_format_check CHECK (response_format IN ('JSON', 'XML', 'HTML_TABLE', 'HTML_PAGE'));

ALTER TABLE lh_notice_candidates ADD COLUMN IF NOT EXISTS district_name text;
ALTER TABLE lh_notice_candidates ADD COLUMN IF NOT EXISTS block_name text;
ALTER TABLE lh_notice_candidates ADD COLUMN IF NOT EXISTS address_raw text;
ALTER TABLE lh_notice_candidates ADD COLUMN IF NOT EXISTS notice_supply_units integer CHECK (notice_supply_units IS NULL OR notice_supply_units >= 0);
ALTER TABLE lh_notice_candidates ADD COLUMN IF NOT EXISTS detail_metadata jsonb;

COMMIT;
