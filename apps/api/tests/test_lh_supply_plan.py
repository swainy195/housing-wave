from apps.api.ingest.lh_supply_plan import parse_month, parse_supply_plan


def test_lh_supply_plan_html_parser_keeps_month_text_and_capital_rows():
    html = """
    <p class='bbs_total'>전체 <strong>128 </strong>건</p>
    <table><tbody>
      <tr><td>서울특별시</td><td>행복주택</td><td>성남금토 A2</td><td>26</td><td>47</td><td>2026년07월</td><td>2027년01월</td><td>경기남부지역본부</td><td></td></tr>
      <tr><td>부산광역시</td><td>행복주택</td><td>제외 대상</td><td>26</td><td>1</td><td>2026년07월</td><td>2027년01월</td><td>부산울산지역본부</td><td></td></tr>
    </tbody></table>
    """
    rows, total = parse_supply_plan(html)
    assert total == 128
    assert rows == [{"region_name": "서울특별시", "housing_type": "행복주택", "housing_name": "성남금토 A2", "exclusive_area": "26", "supply_units": 47, "planned_supply_period": "2026년07월", "planned_move_in_period": "2027년01월", "regional_headquarters": "경기남부지역본부", "note": ""}]
    assert parse_month(rows[0]["planned_supply_period"]) == (2026, 7)
