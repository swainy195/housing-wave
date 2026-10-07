"""Fetch all persisted LH notice detail pages and retain official RAW HTML."""
from __future__ import annotations
import hashlib,json,os
from datetime import date
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine,text
from apps.api.ingest.lh_notice_detail import LhNoticeDetailAdapter
from apps.api.repositories.postgres_repository import sqlalchemy_database_url
from apps.api.scripts.ingest_lh_supply_plan import stable_id

ROOT=Path(__file__).resolve().parents[3];SOURCE_ID='DS-LH-HOUSING-NOTICE';SYSTEM='LH_NOTICE_DETAIL'
def main()->None:
 load_dotenv(ROOT/'apps/api/.env');engine=create_engine(sqlalchemy_database_url(os.environ['DATABASE_URL'])); adapter=LhNoticeDetailAdapter()
 with engine.begin() as conn:
  candidates=[dict(row) for row in conn.execute(text("SELECT id,pan_id,detail_url FROM lh_notice_candidates ORDER BY pan_id")).mappings()]
  ok=attachments=districts=blocks=addresses=identifiers=units=0
  for candidate in candidates:
   try: html,meta=adapter.fetch(candidate['detail_url']);ok+=1
   except Exception:
    conn.execute(text("UPDATE lh_notice_candidates SET detail_fetch_status='FAILED',detail_fetched_at=now(),review_reason=CASE WHEN review_reason='' THEN 'DETAIL_FETCH_FAILED' ELSE review_reason END WHERE id=:id"),{'id':candidate['id']});continue
   checksum=hashlib.sha256(html.encode()).hexdigest();raw_id=stable_id('RAW-LHDT-',{'pan_id':candidate['pan_id'],'checksum':checksum})
   conn.execute(text("""INSERT INTO raw_api_records (id,source_id,source_system,endpoint_name,request_key,request_params,raw_payload,response_format,fetched_at,reference_date,http_status,parse_status,checksum) VALUES (:id,:source_id,:system,'notice_detail_html',:pan,CAST(:params AS jsonb),CAST(:payload AS jsonb),'HTML_PAGE',now(),:today,200,'PARSED',:checksum) ON CONFLICT (source_id,checksum) DO UPDATE SET fetched_at=EXCLUDED.fetched_at,parse_status='PARSED'"""),{'id':raw_id,'source_id':SOURCE_ID,'system':SYSTEM,'pan':candidate['pan_id'],'params':json.dumps({'source_url':candidate['detail_url']}),'payload':json.dumps(meta,ensure_ascii=False),'today':date.today(),'checksum':checksum})
   conn.execute(text("""UPDATE lh_notice_candidates SET detail_fetch_status='FETCHED',detail_fetched_at=now(),district_name=:district,block_name=:block,address_raw=:address,notice_supply_units=:units,detail_metadata=CAST(:metadata AS jsonb),review_reason=CASE WHEN project_match_status='MATCHED' THEN review_reason ELSE 'NO_STRONG_MATCH' END WHERE id=:id"""),{'id':candidate['id'],'district':meta.get('district_name'),'block':meta.get('block_name'),'address':meta.get('address_raw'),'units':meta.get('notice_supply_units'),'metadata':json.dumps(meta,ensure_ascii=False)})
   attachments+=int(bool(meta['attachment_links']));districts+=int(bool(meta.get('district_name')));blocks+=int(bool(meta.get('block_name')));addresses+=int(bool(meta.get('address_raw')));identifiers+=int(bool(meta['official_identifiers']));units+=int(meta.get('notice_supply_units') is not None)
 print(json.dumps({'candidates':len(candidates),'detail_success':ok,'attachments':attachments,'districts':districts,'blocks':blocks,'addresses':addresses,'official_identifiers':identifiers,'notice_supply_units':units},ensure_ascii=False))
if __name__=='__main__':main()
