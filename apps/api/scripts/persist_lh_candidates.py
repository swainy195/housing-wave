import hashlib,json,os
from datetime import date,datetime,timezone
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine,text
from apps.api.ingest.lh_housing_notice import LhHousingNoticeAdapter,normalize,REGION_CODES
from apps.api.repositories.postgres_repository import sqlalchemy_database_url
ROOT=Path(__file__).resolve().parents[3]
SOURCE_ID='DS-LH-HOUSING-NOTICE'; SOURCE_SYSTEM='LH_HOUSING_NOTICE'; ENDPOINT='lhLeaseNoticeInfo1'
def d(value):
    if not value:return None
    for fmt in ('%Y.%m.%d','%Y%m%d','%Y-%m-%d'):
        try:return datetime.strptime(value,fmt).date()
        except ValueError:pass
    return None
def run():
 load_dotenv(ROOT/'apps/api/.env'); key=os.getenv('LH_HOUSING_NOTICE_API_KEY'); url=os.getenv('DATABASE_URL')
 if not key or not url: raise SystemExit('LH_HOUSING_NOTICE_API_KEY and DATABASE_URL are required')
 e=create_engine(sqlalchemy_database_url(url)); out={r:0 for r in REGION_CODES}
 with e.begin() as c:
  c.execute(text("""INSERT INTO data_sources (id,organization_id,source_name,source_url,source_type,collection_method,reference_date,collected_at,validation_status,is_demo) VALUES (:id,'ORG-LH','LH 분양임대공고문 조회 서비스','https://www.data.go.kr/data/15058530/openapi.do','API','API',:rd,:at,'RAW',false) ON CONFLICT (id) DO UPDATE SET collected_at=EXCLUDED.collected_at"""),{'id':SOURCE_ID,'rd':date.today(),'at':datetime.now(timezone.utc)})
  for region in REGION_CODES:
   rows=LhHousingNoticeAdapter(key).fetch(region,date(2026,8,5),date(2026,10,5),page_size=3)
   for raw in rows:
    n=normalize(raw); payload=json.dumps(raw,ensure_ascii=False,sort_keys=True); checksum=hashlib.sha256(payload.encode()).hexdigest(); rawid='RAW-LH-'+checksum[:20]; pan=n['external_id']
    c.execute(text("""INSERT INTO raw_api_records (id,source_id,source_system,endpoint_name,request_key,request_params,raw_payload,response_format,fetched_at,reference_date,http_status,parse_status,checksum) VALUES (:id,:sid,:sys,:ep,:key,CAST(:params AS jsonb),CAST(:payload AS jsonb),'JSON',now(),:rd,200,'REVIEW_REQUIRED',:checksum) ON CONFLICT (source_id,checksum) DO NOTHING"""),{'id':rawid,'sid':SOURCE_ID,'sys':SOURCE_SYSTEM,'ep':ENDPOINT,'key':pan,'params':json.dumps({'CNP_CD':REGION_CODES[region]}),'payload':payload,'rd':date.today(),'checksum':checksum})
    c.execute(text("""INSERT INTO lh_notice_candidates (id,pan_id,pan_name,region_code,region_name,upper_supply_type,supply_type,notice_status,notice_start_date,closing_date,detail_url,raw_record_id,source_id,review_reason,validation_status,is_demo) VALUES (:id,:pan,:name,:rc,:rn,:upper,:stype,:status,:start,:end,:url,:raw,:sid,'MISSING_ADDRESS,MISSING_PROJECT_IDENTIFIER,MISSING_SUPPLY_UNITS','REVIEW_REQUIRED',false) ON CONFLICT (pan_id) DO UPDATE SET pan_name=EXCLUDED.pan_name,notice_status=EXCLUDED.notice_status,notice_start_date=EXCLUDED.notice_start_date,closing_date=EXCLUDED.closing_date,detail_url=EXCLUDED.detail_url,raw_record_id=EXCLUDED.raw_record_id,updated_at=now()"""),{'id':'LHC-'+hashlib.sha256(pan.encode()).hexdigest()[:20],'pan':pan,'name':n['name'],'rc':REGION_CODES[region],'rn':n['region'],'upper':raw.get('UPP_AIS_TP_NM'),'stype':n['supply_type'],'status':n['notice_status'],'start':d(n['announcement_date']),'end':d(n['application_end_date']),'url':n['source_url'],'raw':rawid,'sid':SOURCE_ID}); out[region]+=1
 print(json.dumps({'candidates':out,'total':sum(out.values()),'review_required':sum(out.values())},ensure_ascii=False))
if __name__=='__main__':run()
