from apps.api.ingest.lh_move_in_plan import district_key, exact_match, extract_blocks, normalize_block_name, parse_month, parse_move_in_plan


def test_move_in_html_parser_preserves_construction_units_and_month():
    html = """<p>전체 <strong>6</strong>건</p><table><tbody><tr><td>경기도</td><td>분양주택</td><td>성남복정1 A-2BL</td><td>387</td><td>2026.12</td><td>2026.12.22~2027.02.20</td><td></td></tr></tbody></table>"""
    rows, total = parse_move_in_plan(html)
    assert total == 6 and rows[0]["construction_units"] == 387
    assert rows[0]["planned_move_in_period"] == "2026.12"
    assert parse_month(rows[0]["planned_move_in_period"]) == (2026, 12)


def test_block_normalization_and_exact_match_do_not_use_fuzzy_name():
    assert normalize_block_name("A-1BL") == normalize_block_name("a1 블록")
    assert extract_blocks("성남 금토 A-1BL") == ("A1",)
    assert district_key("성남금토 A-1BL") == district_key("성남금토 A1")
    projects = [{"id": "P1", "name": "성남금토 A1", "province": "경기", "housing_type": "국민임대", "planned_units": 100}]
    row = {"province": "경기", "district_block_name": "성남금토 A-1BL", "district_block_name_normalized": normalize_block_name("성남금토 A-1BL"), "blocks": extract_blocks("성남금토 A-1BL"), "housing_type": "국민임대", "construction_units": 120}
    matched, rule, _ = exact_match(row, projects)
    assert matched and matched["id"] == "P1" and rule == "EXACT_BLOCK"
    ambiguous = projects + [{"id": "P2", "name": "성남금토 A1", "province": "경기", "housing_type": "국민임대", "planned_units": 50}]
    matched, rule, evidence = exact_match(row, ambiguous)
    assert matched is None and rule is None and evidence["reason"] == "AMBIGUOUS_EXACT_MATCH"
    different_district = {**row, "district_block_name": "성남복정1 A1", "district_block_name_normalized": normalize_block_name("성남복정1 A1"), "blocks": extract_blocks("성남복정1 A1")}
    matched, rule, evidence = exact_match(different_district, projects)
    assert matched is None and rule is None and evidence["reason"] == "NO_EXACT_MATCH"
