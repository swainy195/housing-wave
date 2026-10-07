from apps.api.ingest.lh_project_notice_search import parse_results, search_queries

def test_project_queries_are_specific_and_deduplicated():
    values=search_queries({"name":"화성동탄2 A-3BL","housing_type":"행복주택"})
    assert values[0]=="화성동탄2 A-3BL" and "행복주택" not in values
    assert all(len(v.replace(" ","")) >= 3 for v in values)

def test_parse_official_notice_result_preserves_pan_and_detail_url():
    html='<table><tr><td>1</td><td>행복주택</td><td><a class="wrtancInfoBtn" data-id1="PAN1" data-id2="03" data-id3="06" data-id4="10">공고</a></td><td>경기도</td><td></td><td>2026.01.01</td><td>2026.01.10</td><td>마감</td></tr></table>'
    row=parse_results(html)[0]
    assert row["pan_id"]=="PAN1" and "panId=PAN1" in row["detail_url"] and row["region"]=="경기도"
