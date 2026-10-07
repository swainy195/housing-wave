# Deployment runbook

## Architecture

Vercel hosts `apps/web` (React/Vite). Render hosts FastAPI from the repository root. The API connects server-side to Supabase PostgreSQL/PostGIS.

## Vercel

- Root directory: `apps/web`
- Install command: `npm install`
- Build command: `npm run build`
- Output directory: `dist`
- Environment variable: `VITE_API_BASE_URL=https://<render-service-domain>`

Only the public HTTPS API base URL belongs in Vercel. Do not add database credentials, API keys, or service-role credentials to Vercel.

## Render

The repository includes `render.yaml`. Set these secret values in the Render dashboard:

- `DATABASE_URL`: existing Supabase PostgreSQL connection URL
- `CORS_ALLOWED_ORIGINS`: exact Vercel production URL, without a trailing slash
- Optional server-side keys: `LH_HOUSING_NOTICE_API_KEY`, `SEOUL_OPEN_DATA_API_KEY`

`DATABASE_MODE=postgres` and `APP_ENV=production` are configured in the Blueprint. The service health check is `/health`.

## Release validation

1. Confirm `GET https://<render-service-domain>/health` returns `PostgresRepository`, `postgres`, and `MIXED`.
2. Confirm the dashboard APIs return HTTP 200: summary, pipeline, coverage, projects, upcoming, and review candidates.
3. Open the Vercel URL and confirm no CORS, mixed-content, or API errors.
4. Record the two public URLs in the README after deployment.

## Seoul Open Data readiness

The official Seoul Open Data API convention is `http://openapi.seoul.go.kr:8088/{KEY}/json/{SERVICE}/{START}/{END}`. A server-side key is required. No Seoul key is present in the local environment, so no request or data persistence is performed by this deployment preparation.
