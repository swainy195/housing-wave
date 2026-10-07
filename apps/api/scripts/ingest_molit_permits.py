"""Manual, parcel-scoped ingestion for MOLIT Housing-HUB permit records."""
import argparse
import json
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from apps.api.ingest.molit_housing_permit import MolitHousingPermitAdapter, MolitPermitPersister, ParcelQuery, normalize_item

ROOT = Path(__file__).resolve().parents[3]


def main() -> None:
    load_dotenv(ROOT / "apps" / "api" / ".env")
    parser = argparse.ArgumentParser(description="Fetch one official MOLIT Housing-HUB parcel query; no broad region scan is supported by this API.")
    parser.add_argument("--region", required=True, choices=("seoul", "gyeonggi", "incheon"))
    parser.add_argument("--sigungu-cd", required=True)
    parser.add_argument("--bjdong-cd", required=True)
    parser.add_argument("--plat-gb-cd", default="0")
    parser.add_argument("--bun", required=True)
    parser.add_argument("--ji", default="0000")
    parser.add_argument("--limit", type=int, default=20, choices=range(1, 51))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--persist", action="store_true")
    args = parser.parse_args()
    if args.dry_run == args.persist:
        parser.error("choose exactly one of --dry-run or --persist")
    api_key = os.getenv("MOLIT_HOUSING_PERMIT_API_KEY")
    if not api_key:
        raise SystemExit("MOLIT_HOUSING_PERMIT_API_KEY is required; the key is never logged")
    parcel = ParcelQuery(args.region, args.sigungu_cd, args.bjdong_cd, args.plat_gb_cd, args.bun, args.ji)
    payload, status, items, total, response_format = MolitHousingPermitAdapter(api_key).fetch(parcel, num_rows=args.limit)
    normalized = [normalize_item(item, parcel, date.today()) for item in items]
    result = {"endpoint": "getHpBasisOulnInfo", "region": args.region, "fetched": len(items), "total_count": total, "normalized": sum(row["validation_status"] == "VALIDATED" for row in normalized), "review_required": sum(row["validation_status"] != "VALIDATED" for row in normalized), "http_status": status}
    if args.persist:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise SystemExit("DATABASE_URL is required for --persist")
        result.update(MolitPermitPersister(database_url).persist(parcel, payload, status, response_format, normalized))
    print(json.dumps(result, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
