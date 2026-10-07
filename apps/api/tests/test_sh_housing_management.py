from datetime import date

from apps.api.ingest.sh_housing_management import nullable_integer, parse_open_date
from apps.api.scripts.ingest_sh_housing_management import dry_run_summary, source_record_id


def test_excel_serial_open_date_is_parsed_conservatively():
    assert parse_open_date("33618") == (date(1992, 1, 15), "EXCEL_SERIAL")
    assert parse_open_date("not-a-date") == (None, None)
    assert parse_open_date(None) == (None, None)


def test_nullable_households_does_not_convert_missing_to_zero():
    assert nullable_integer(None) is None
    assert nullable_integer("") is None
    assert nullable_integer("1,234") == 1234


def test_source_record_id_is_stable_for_same_official_row():
    row = {"GU_NM": "강남구", "APT_NM": "개포", "APT_TYPE": "임대", "APT_CNT": "10", "APT_OPEN_DT": "33618", "APT_ADDR": "주소", "APT_ZIP": "00000", "APT_TEL": "02"}
    assert source_record_id(row) == source_record_id(dict(row))


def test_dry_run_summary_only_includes_schema_metadata():
    class Result:
        status_code = 200; result_code = "INFO-000"; result_message = "정상 처리되었습니다"; total_count = 1
        rows = [{"GU_NM": "강남구", "APT_NM": "개포", "APT_TYPE": "임대", "APT_CNT": "10", "APT_OPEN_DT": "33618", "APT_ADDR": "주소", "APT_ZIP": "00000", "APT_TEL": "02"}]
        envelope_keys = ["RESULT", "list_total_count", "row"]
    summary = dry_run_summary(Result())
    assert summary["required_fields_present"] == {key: True for key in Result.rows[0]}
    assert summary["apt_open_dt_date_format"] == "EXCEL_SERIAL"
