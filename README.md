# Sumo Social API

A modular FastAPI backend for connecting creator social accounts and synchronizing existing video/content data. Platform-specific OAuth and API calls live in `app/integrations`; routes call services, and services persist normalized records.

## Installation

```powershell
C:/Users/divya/AppData/Local/Python/pythoncore-3.14-64/python.exe -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `DATABASE_URL` and `SECRET_KEY` in `.env`. Start PostgreSQL and create the `sumo` database, then run:

`ENABLED_SOCIAL_PLATFORMS` controls which platform APIs are available. It defaults to `youtube,facebook`; add a platform name there when its integration is ready to re-enable.

```powershell
alembic upgrade head

uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`; interactive docs are at `/docs` and `/redoc`. `GET /health` returns `{ "status": "ok" }`.

## OAuth and API usage

Create OAuth applications in Google Cloud (YouTube) and Meta for Developers (Facebook Pages). Register each callback URI from `.env.example`, then fill in the matching client variables. The connect endpoint returns a provider authorization URL:

```text
GET /api/v1/social/{platform}/connect
GET /api/v1/social/{platform}/callback?code=...&state=...
GET /api/v1/social/accounts
GET /api/v1/social/accounts/{account_id}/videos
POST /api/v1/social/accounts/{account_id}/sync
```

Create a creator or brand account, then send the returned bearer token as `Authorization: Bearer <access_token>` on protected endpoints:

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
```

Registration requires a unique `login_id`, password, and `role` (`creator` or `brand`). Passwords are stored as PBKDF2 hashes, and access tokens are signed and expire according to `ACCESS_TOKEN_EXPIRE_MINUTES`. Tokens are stored server-side and are never returned by API schemas or logged.

YouTube sync handles API page tokens. Facebook sync handles Graph API cursors.
YouTube analytics are available at
`GET /api/v1/analytics/accounts/{account_id}/youtube?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`.
The response includes views, likes, comments, shares, watch time, retention,
subscribers gained/lost, traffic sources, geography, daily/monthly data,
playback location, and age/gender. Reconnect YouTube accounts after enabling
analytics so the OAuth consent includes the analytics read-only scope.

## Creator and brand workflows

Creator and brand profiles use the authenticated bearer-token identity. The API supports public creator discovery, brand campaigns, collaboration invitations and responses, content drafts, scheduled calendar entries, and analytics over synced video metrics.

To associate a social account with a creator, call the existing `/api/v1/social/{platform}/connect` flow with the creator's bearer token. The OAuth callback stores the account under the signed OAuth state user ID, and creator profile/discovery responses include enabled connected accounts with public profile metadata only; access and refresh tokens are never included.

```text
POST/PATCH/GET /api/v1/creators/me
GET            /api/v1/creators/discover
GET            /api/v1/creators/{creator_user_id}
GET            /api/v1/analytics/creators/{creator_user_id}
POST/PATCH/GET /api/v1/brands/me
POST/GET       /api/v1/brands/me/campaigns
GET            /api/v1/campaigns
POST/GET       /api/v1/brands/me/collaborations
GET/PATCH      /api/v1/creators/me/collaborations
POST/GET       /api/v1/content
GET            /api/v1/content/calendar?start=...&end=...
GET            /api/v1/content/history
GET            /api/v1/analytics/overview
POST/GET       /api/v1/analytics/accounts/{account_id}/snapshots
```

Scheduled content is stored for calendar and history workflows; this API does not yet run a background scheduler. `POST /api/v1/content/{content_id}/publish` returns `501` because the current Facebook integration is read-only and YouTube OAuth requests read-only access. Enabling publishing requires provider write permissions and upload implementations. Audience snapshots can be recorded through the analytics endpoint; current integrations do not fetch follower counts.

## Tests

```powershell
pytest
```

Tests mock or avoid external platform calls. Add provider-specific mocked response tests as each approved API contract is finalized.
