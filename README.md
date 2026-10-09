# Sumo Social API

A modular FastAPI backend for connecting creator social accounts and synchronizing existing video/content data. Platform-specific OAuth and API calls live in `app/integrations`; routes call services, and services persist normalized records.

## Installation

```powershell
C:/Users/divya/AppData/Local/Python/pythoncore-3.14-64/python.exe -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `DATABASE_URL`, `SECRET_KEY`, and `CORS_ORIGINS` in `.env`. `CORS_ORIGINS` accepts
multiple origins separated by commas, for example
`CORS_ORIGINS=http://localhost:3000,https://app.example.com`. Start PostgreSQL and
create the `sumo` database, then run:

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
DELETE /api/v1/social/accounts/{account_id}
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

Content can use `target_content` on `POST /api/v1/content` or
`PATCH /api/v1/content/{content_id}` to provide a different `post_type`,
`media_url`, and caption for each selected social account. Facebook targets can
be `video`, `image`, or `text`. YouTube targets must be `video` because the
public YouTube API does not support Community text/image posts. Any target
without an override uses the top-level `media_url` and caption.

### Publishing a video to a Facebook Page

1. Create a Meta app at [Meta for Developers](https://developers.facebook.com/),
   configure Facebook Login, and set the callback URL from `.env.example`.
2. Set `FACEBOOK_APP_ID`, `FACEBOOK_APP_SECRET`, `FACEBOOK_CONFIG_ID`, and
   `FACEBOOK_REDIRECT_URI` in `.env`. Keep the app secret out of source control.
3. Ensure the Facebook Login configuration has these permissions available:
   `public_profile`, `pages_show_list`, `pages_manage_posts`, and
   `pages_read_engagement`. During development, the Facebook user must be an
   administrator, developer, or tester of the app and must have sufficient
   access to the Page. Production use may require Meta App Review and business
   verification. Dashboard configuration alone does not grant permissions to
   an existing User Access Token.
4. Register and log in through the API, then open the URL returned by
   `GET /api/v1/social/facebook/connect` while authenticated. Complete the
   Facebook consent screen and approve all requested permissions. The callback
   verifies the granted permissions before storing the connected Facebook
   account. If permissions were changed, use the connect URL again to perform
   a fresh reconnect.
5. Upload a publicly reachable video with `POST /api/v1/content/upload`, create
   content using its `media_url` and the connected Facebook account ID, then
   publish it:

```bash
curl -X POST http://localhost:8000/api/v1/content/upload \
  -H "Authorization: Bearer YOUR_SUMO_TOKEN" \
  -F "file=@./video.mp4"

curl -X POST http://localhost:8000/api/v1/content \
  -H "Authorization: Bearer YOUR_SUMO_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "caption": "My first Facebook Page video",
    "media_url": "https://res.cloudinary.com/example/video/upload/video.mp4",
    "social_account_ids": [31]
  }'

curl -X POST http://localhost:8000/api/v1/content/CONTENT_ID/publish \
  -H "Authorization: Bearer YOUR_SUMO_TOKEN"
```

The Facebook integration discovers a managed Page from the connected account and
uploads the public video URL to that Page. Cloudinary is already configured as
the default video storage provider. This flow publishes videos; it does not
publish to personal Facebook profiles.

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
POST            /api/v1/content/upload
GET            /api/v1/content/calendar?start=...&end=...
GET            /api/v1/content/history
GET            /api/v1/analytics/overview
POST/GET       /api/v1/analytics/accounts/{account_id}/snapshots
```

Scheduled content is stored for calendar and history workflows; this API does not yet run a background scheduler. `POST /api/v1/content/{content_id}/publish` publishes the content media URL to every selected account. Reconnect YouTube accounts after this change so the consent includes `youtube.upload`; Facebook publishing requires a Page account connected with `pages_manage_posts` and a publicly reachable video URL. YouTube uploads are private by default and can be made public through the provider after publishing. Audience snapshots can be recorded through the analytics endpoint; current integrations do not fetch follower counts.

Video files can be uploaded directly to Cloudinary before creating content:

```text
POST /api/v1/content/upload
Content-Type: multipart/form-data
Authorization: Bearer YOUR_TOKEN
file=@./video.mp4
```

The response contains `media_url`. Pass that value as `media_url` when creating
content, then call the publish endpoint. Configure `CLOUDINARY_CLOUD_NAME`,
`CLOUDINARY_API_KEY`, and `CLOUDINARY_API_SECRET` in `.env`; the default upload
limit is 500 MB and can be changed with `MAX_VIDEO_UPLOAD_BYTES`.

## Tests

```powershell
pytest
```

Tests mock or avoid external platform calls. Add provider-specific mocked response tests as each approved API contract is finalized.
