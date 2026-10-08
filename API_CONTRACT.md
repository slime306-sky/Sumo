# Sumo Social API Contract

This document describes the API implemented by the current FastAPI backend. Paths use the `/api/v1` prefix unless otherwise noted.

## API conventions

- Base path: `{{API_BASE_URL}}/api/v1`
- Content type for JSON requests: `application/json`
- Datetimes use ISO 8601. Scheduled content must include a timezone and be in the future.
- Supported social platforms: `facebook`, `youtube`. Other platform names fail request validation with `422`.
- Most creator/brand-owned endpoints require `Authorization: Bearer <access_token>`.
- Public discovery routes do not require authentication.

### Production OAuth configuration

For a deployed Render service, configure the provider redirect URIs with the
public HTTPS service URL, not `localhost`:

```text
https://YOUR-RENDER-DOMAIN.onrender.com/api/v1/social/facebook/callback
https://YOUR-RENDER-DOMAIN.onrender.com/api/v1/social/youtube/callback
```

Set the matching values in Render:

```env
FACEBOOK_REDIRECT_URI=https://YOUR-RENDER-DOMAIN.onrender.com/api/v1/social/facebook/callback
YOUTUBE_REDIRECT_URI=https://YOUR-RENDER-DOMAIN.onrender.com/api/v1/social/youtube/callback
```

The callback URL must match the provider configuration exactly. Localhost
redirects may remain registered for local development.

### Authentication

`POST /auth/register` accepts `{ "login_id": "creator_1", "password": "a-strong-password", "role": "creator" }`.
The role must be `creator` or `brand`. `POST /auth/login` accepts `login_id` and `password`.
Both endpoints return `user_id`, `role`, `access_token`, and `token_type: "bearer"`.
Send the access token as `Authorization: Bearer <access_token>` to protected endpoints.
Tokens are signed with `SECRET_KEY` and expire after `ACCESS_TOKEN_EXPIRE_MINUTES`.
- Tokens are never included in social-account or creator-profile responses.

### Common errors

FastAPI request validation errors return `422`, typically in this shape:

```json
{
  "detail": [
    {
      "loc": ["body", "field"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```

Application errors generally return:

```json
{"detail": "Human-readable error"}
```

Provider rate limits return `429`; provider integration errors return `502`.

## Health

### `GET /health`

No headers or body required.

**200 response**

```json
{"status": "ok"}
```

## Social accounts

### `GET /social/{platform}/connect`

Begins OAuth for the specified supported platform. Authenticate the request with the creator.s bearer token so the callback state associates the account with the correct owner.

**Path parameter**

| Name | Type | Values |
|---|---|---|
| `platform` | string | `facebook`, `youtube` |

**Headers**

| Name | Required | Description |
|---|---|---|
| `Authorization: Bearer <access_token>` | Yes | Bearer access token identifying the account owner |

**200 response**

```json
{"authorization_url": "https://provider.example/oauth?..."}
```

**Errors:** `404` if the platform is temporarily disabled by configuration; `422` for an unsupported platform.

### `GET /social/{platform}/callback`

OAuth redirect target. The provider supplies `code`; the API uses the signed
state to recover the owner ID. No application bearer token is required on this
provider callback because ownership is established by the signed state created
by the authenticated `/connect` request.

**Query parameters**

| Name | Type | Required |
|---|---|---|
| `code` | string | Yes |
| `state` | string | Yes |

**200 response: `SocialAccountResponse`**

```json
{
  "id": 31,
  "user_id": 7,
  "platform": "youtube",
  "platform_user_id": "UCexample",
  "platform_username": "@creator",
  "profile_name": "Creator Channel",
  "profile_image_url": "https://images.example/avatar.jpg",
  "token_expires_at": null,
  "is_influencer": false,
  "is_active": true
}
```

`access_token` and `refresh_token` are deliberately omitted.

**Errors:** `400` invalid OAuth state; `404` temporarily disabled platform; `422` unsupported platform; `502` provider connection failure.

### `GET /social/accounts`

Lists the current user's active accounts on enabled platforms.

**Headers:** `Authorization: Bearer <access_token>`.

**200 response:** array of `SocialAccountResponse` objects, as above.

### `PATCH /social/accounts/{account_id}/influencer`

Sets whether a connected account is marked as an influencer account. This is an idempotent set operation.

**Headers:** `Authorization: Bearer <access_token>`.

**Request body**

```json
{"is_influencer": true}
```

**200 response:** updated `SocialAccountResponse`.

**Errors:** `404` account not found for this user; `422` invalid/missing boolean.

### `GET /social/accounts/{account_id}/videos`

Returns videos already stored for an owned active account. It does not trigger a provider sync.

**Headers:** `Authorization: Bearer <access_token>`.

**200 response**

```json
{
  "platform": "youtube",
  "count": 1,
  "videos": [
    {
      "platform_video_id": "video-123",
      "title": "A video",
      "description": null,
      "url": "https://www.youtube.com/watch?v=video-123",
      "thumbnail_url": null,
      "published_at": "2026-10-01T12:00:00Z",
      "duration": 120,
      "view_count": 1500,
      "like_count": 80,
      "comment_count": 9
    }
  ]
}
```

**Errors:** `404` account not found for this user; `404` temporarily disabled platform.

### `POST /social/accounts/{account_id}/sync`

Fetches and persists provider videos for an owned active account.

**Headers:** `Authorization: Bearer <access_token>`.

No request body.

**200 response**

```json
{
  "account_id": 31,
  "platform": "youtube",
  "count": 1,
  "videos": [
    {
      "platform_video_id": "video-123",
      "title": "A video",
      "description": null,
      "url": "https://www.youtube.com/watch?v=video-123",
      "thumbnail_url": null,
      "published_at": "2026-10-01T12:00:00Z",
      "duration": 120,
      "view_count": 1500,
      "like_count": 80,
      "comment_count": 9
    }
  ]
}
```

**Errors:** `404` account not found or platform disabled; `429` provider rate limit; `502` provider sync error.

## Creator profiles and discovery

### Creator profile fields

`CreatorProfileResponse` contains:

| Field | Type | Notes |
|---|---|---|
| `id` | integer | Profile record ID |
| `user_id` | integer | Owner ID |
| `display_name` | string | Required, 1-255 characters |
| `bio` | string or null | |
| `niche` | string or null | Maximum 120 characters |
| `location` | string or null | Maximum 255 characters |
| `is_public` | boolean | Defaults to `true` |
| `created_at` | datetime | |
| `social_accounts` | array | Active, enabled linked accounts; contains public metadata only |

Each `social_accounts` entry contains `platform`, `platform_username`, `profile_name`, `profile_image_url`, and `is_influencer`. Tokens and internal account IDs are not exposed there.

### `POST /creators/me`

Creates or updates the current user's creator profile (upsert behavior).

**Headers:** `Authorization: Bearer <access_token>`.

**Request body**

```json
{
  "display_name": "Taylor Creator",
  "bio": "Food and travel videos",
  "niche": "food",
  "location": "Seattle",
  "is_public": true
}
```

Only `display_name` is required; omitted optional fields use the defaults shown above.

**201 response:** `CreatorProfileResponse`, including connected `social_accounts`.

### `GET /creators/me`

Returns the current user's creator profile and connected social accounts.

**Headers:** `Authorization: Bearer <access_token>`.

**200 response:** `CreatorProfileResponse`.

**Errors:** `404` creator profile not found.

### `PATCH /creators/me`

Updates an existing creator profile. All fields are optional; supplied fields are updated.

**Headers:** `Authorization: Bearer <access_token>`.

**Request body example**

```json
{"bio": "Updated creator bio", "is_public": false}
```

**200 response:** updated `CreatorProfileResponse`.

**Errors:** `404` creator profile not found; `422` invalid field values.

### `GET /creators/discover?niche={niche}`

Lists public creator profiles. `niche` is an optional substring filter, maximum 120 characters.

**200 response:** array of `CreatorProfileResponse` objects, including connected social-account metadata.

### `GET /creators/{creator_user_id}`

Returns one public creator profile by owner ID.

**200 response:** `CreatorProfileResponse`.

**Errors:** `404` if no public profile exists for that user ID.

## Brand profiles

### Brand profile fields

`BrandProfileResponse` contains `id`, `user_id`, `company_name`, `description`, `website`, `industry`, `logo_url`, and `created_at`.

### `POST /brands/me`

Creates or updates the current user's brand profile (upsert behavior).

**Headers:** `Authorization: Bearer <access_token>`.

**Request body**

```json
{
  "company_name": "Northstar Foods",
  "description": "A packaged food company",
  "website": "https://brand.example",
  "industry": "Food",
  "logo_url": "https://brand.example/logo.png"
}
```

`company_name` is required; all other fields are optional.

**201 response:** `BrandProfileResponse`.

### `GET /brands/me`

Returns the current user's brand profile.

**Headers:** `Authorization: Bearer <access_token>`.

**200 response:** `BrandProfileResponse`.

**Errors:** `404` brand profile not found.

### `PATCH /brands/me`

Updates an existing brand profile; fields are optional.

**Headers:** `Authorization: Bearer <access_token>`.

**Request body example**

```json
{"description": "Updated company description", "industry": "Food and beverage"}
```

**200 response:** updated `BrandProfileResponse`.

**Errors:** `404` brand profile not found; `422` invalid field values.

## Campaigns and collaborations

### Campaign fields

`CampaignResponse` contains `id`, `brand_user_id`, `title`, `description`, `requirements`, `budget`, `starts_at`, `ends_at`, `status`, and `created_at`. Budget is a non-negative decimal or `null`. Campaign statuses accepted on update are `draft`, `open`, `active`, `completed`, and `cancelled`; newly created campaigns start as `open`.

### `POST /brands/me/campaigns`

Creates a campaign. The current user must have a brand profile.

**Headers:** `Authorization: Bearer <access_token>`.

**Request body**

```json
{
  "title": "Summer launch",
  "description": "Promote our seasonal range",
  "requirements": "One short-form video",
  "budget": 2500.00,
  "starts_at": "2026-11-01T00:00:00Z",
  "ends_at": "2026-11-30T23:59:59Z"
}
```

Only `title` is required. `ends_at` cannot precede `starts_at`.

**201 response:** `CampaignResponse` with `status: "open"`.

**Errors:** `400` brand profile is missing or campaign dates are invalid; `422` invalid body.

### `GET /brands/me/campaigns`

Lists campaigns owned by the current brand.

**Headers:** `Authorization: Bearer <access_token>`.

**200 response:** array of `CampaignResponse` objects.

### `PATCH /brands/me/campaigns/{campaign_id}`

Updates an owned campaign. All request fields are optional.

**Headers:** `Authorization: Bearer <access_token>`.

**Request body example**

```json
{"status": "active", "budget": 3000}
```

**200 response:** updated `CampaignResponse`.

**Errors:** `400` brand profile missing or invalid dates; `404` campaign not found/owned; `422` invalid field values.

### `GET /campaigns`

Lists campaigns whose status is `open`; this route is public.

**200 response:** array of `CampaignResponse` objects.

### `POST /brands/me/collaborations`

Sends an invitation to a public creator, optionally tied to a campaign owned by the brand.

**Headers:** `Authorization: Bearer <access_token>`.

**Request body**

```json
{
  "creator_user_id": 22,
  "campaign_id": 8,
  "message": "We'd like to collaborate on our summer launch."
}
```

`creator_user_id` is required; `campaign_id` and `message` are optional.

**201 response: `CollaborationResponse`**

```json
{
  "id": 41,
  "brand_user_id": 33,
  "creator_user_id": 22,
  "campaign_id": 8,
  "message": "We'd like to collaborate on our summer launch.",
  "status": "pending",
  "created_at": "2026-10-08T12:00:00Z"
}
```

**Errors:** `400` no brand profile, creator is not public/not found, or campaign is not owned by the brand; `422` invalid body.

### `GET /brands/me/collaborations`

Lists requests sent by the current brand.

**Headers:** `Authorization: Bearer <access_token>`.

**200 response:** array of `CollaborationResponse` objects.

### `GET /creators/me/collaborations`

Lists requests received by the current creator.

**Headers:** `Authorization: Bearer <access_token>`.

**200 response:** array of `CollaborationResponse` objects.

### `PATCH /creators/me/collaborations/{request_id}`

Accepts or declines a pending collaboration request.

**Headers:** `Authorization: Bearer <access_token>`.

**Request body**

```json
{"status": "accepted"}
```

Allowed values: `accepted`, `declined`.

**200 response:** updated `CollaborationResponse`.

**Errors:** `404` request not found/owned; `409` request is not pending; `422` invalid status.

### `PATCH /brands/me/collaborations/{request_id}`

Updates progress on an accepted request.

**Headers:** `Authorization: Bearer <access_token>`.

**Request body**

```json
{"status": "in_progress"}
```

Allowed values: `in_progress`, `completed`, `cancelled`. The request must already be `accepted` or `in_progress`.

**200 response:** updated `CollaborationResponse`.

**Errors:** `404` request not found/owned; `409` invalid transition; `422` invalid status.

## Content management

### Content fields

`ContentResponse` contains `id`, `creator_user_id`, `caption`, `media_url`, `status`, `scheduled_at`, `published_at`, `created_at`, and `targets`. Each target contains `id`, `social_account_id`, `platform_post_id`, `published_url`, and `status`.

Content status is `draft`, `scheduled`, or `published` in current service workflows. Target status starts as `pending`.

### `POST /content`

Creates a content draft or a scheduled item. At least one of `caption` or `media_url` must be non-empty. Every target account must belong to the current user and be active/enabled.

**Headers:** `Authorization: Bearer <access_token>`.

**Request body**

```json
{
  "caption": "A new video is coming soon",
  "media_url": "https://cdn.example/video.mp4",
  "social_account_ids": [31, 32],
  "scheduled_at": "2026-11-05T16:00:00Z"
}
```

All properties are optional except that at least one of `caption` or `media_url` must be supplied. `social_account_ids` defaults to `[]`. `scheduled_at` requires a timezone, a future time, and at least one target account.

**201 response: `ContentResponse`**

```json
{
  "id": 70,
  "creator_user_id": 7,
  "caption": "A new video is coming soon",
  "media_url": "https://cdn.example/video.mp4",
  "status": "scheduled",
  "scheduled_at": "2026-11-05T16:00:00Z",
  "published_at": null,
  "created_at": "2026-10-08T12:00:00Z",
  "targets": [
    {
      "id": 90,
      "social_account_id": 31,
      "platform_post_id": null,
      "published_url": null,
      "status": "pending"
    }
  ]
}
```

**Errors:** `400` invalid schedule or target ownership; `422` request validation error.

### `GET /content`

Lists the current user's content. Optional query parameter: `status` (string; commonly `draft`, `scheduled`, or `published`).

**Headers:** `Authorization: Bearer <access_token>`.

**200 response:** array of `ContentResponse` objects.

### `GET /content/calendar?start={datetime}&end={datetime}`

Lists scheduled items whose `scheduled_at` falls within the given inclusive range. Both parameters are required; `end` must be after `start`.

**Headers:** `Authorization: Bearer <access_token>`.

**200 response:** array of `ContentResponse` objects.

**Errors:** `400` start is not before end; `422` missing/invalid datetime.

### `GET /content/history`

Lists the current user's items with `status: "published"`.

**Headers:** `Authorization: Bearer <access_token>`.

**200 response:** array of `ContentResponse` objects. The current provider integrations do not publish content, so no item is marked published by the publish endpoint yet.

### `GET /content/{content_id}`

Returns one content item owned by the current user.

**Headers:** `Authorization: Bearer <access_token>`.

**200 response:** `ContentResponse`.

**Errors:** `404` content not found/owned.

### `PATCH /content/{content_id}`

Updates an owned, unpublished item. Supported fields: `caption`, `media_url`, `social_account_ids`, `scheduled_at`. Fields are optional. At least one of caption/media URL must remain set. `scheduled_at: null` clears the schedule; a non-null value must be a future timezone-aware datetime with at least one target account. Replacing targets requires all account IDs to belong to the current user.

**Headers:** `Authorization: Bearer <access_token>`.

**Request body example**

```json
{
  "caption": "Updated caption",
  "social_account_ids": [31],
  "scheduled_at": null
}
```

**200 response:** updated `ContentResponse`.

**Errors:** `400` invalid content/schedule/target; `404` item not found/owned; `422` invalid body.

### `POST /content/{content_id}/publish`

No request body. Returns `501 Not Implemented` for an owned content item because the current Facebook and YouTube integrations lack configured publishing permissions and upload implementations.

**Headers:** `Authorization: Bearer <access_token>`.

**Errors:** `404` content not found/owned; `501` publishing is not currently available.

## Analytics

Analytics use synced video rows and explicitly recorded account snapshots. The current integrations do not automatically fetch follower counts.

### Analytics response shape

Account analytics contains:

- `account_id`, `platform`
- `content_count`, `view_count`, `like_count`, `comment_count`
- `follower_count`: most recent recorded non-null count, or `null`
- `follower_growth`: latest minus earliest recorded non-null count, or `null` when fewer than two values exist
- `snapshots`: array of `{id, social_account_id, follower_count, view_count, recorded_at}`

### `GET /analytics/overview`

Returns aggregates for all active accounts belonging to the current user.

**Headers:** `Authorization: Bearer <access_token>`.

**200 response**

```json
{
  "accounts": [
    {
      "account_id": 31,
      "platform": "youtube",
      "content_count": 12,
      "view_count": 5300,
      "like_count": 210,
      "comment_count": 18,
      "follower_count": 1200,
      "follower_growth": 100,
      "snapshots": []
    }
  ],
  "content_count": 12,
  "view_count": 5300,
  "like_count": 210,
  "comment_count": 18
}
```

### `GET /analytics/creators/{creator_user_id}`

Returns the same analytics overview for a public creator. Does not require `Authorization: Bearer <access_token>`.

**200 response:** analytics overview shape above.

**Errors:** `404` no public creator profile found.

### `GET /analytics/accounts/{account_id}`

Returns analytics for an account owned by the current user.

**Headers:** `Authorization: Bearer <access_token>`.

**200 response:** account analytics shape above.

### `GET /analytics/accounts/{account_id}/youtube`

Returns YouTube Analytics API data for an owned YouTube account. `start_date` and
`end_date` are optional ISO dates and default to the previous 28 days.
Dates must be between `2005-02-14` and yesterday, and `start_date` must not be
after `end_date`. YouTube Analytics does not accept the current date as
`endDate`; requesting today returns `422`.

The response contains `summary`, `daily`, `monthly`, `traffic_sources`,
`geography`, `playback_location`, and `age_gender` arrays. The summary and
time-series rows include views, likes, comments, shares, watch time, average
view duration, average view percentage, and subscribers gained/lost where
provided by YouTube. Monthly queries use completed calendar-month boundaries
separately from the requested overall/daily range.

The first YouTube connection must be reconnected after enabling this feature so
the OAuth token includes the `yt-analytics.readonly` scope.

**Errors:** `404` account not found/owned.

### Facebook Page analytics

Facebook Page analytics are not currently exposed by an API endpoint. The
existing Facebook connection stores the connected Facebook identity and
supports the current account/video workflows, but it does not yet select a
Facebook Page, obtain a Page Access Token, or call the Page Insights API.

The planned endpoint is:

```text
GET /analytics/accounts/{account_id}/facebook
```

The planned response will group supported Meta Page Insights by reach/views,
post engagements, reactions, comments, shares, followers/follows/unfollows,
video views and unique viewers, geography, language, daily/weekly/28-day
periods, CTA clicks, post-level performance, and available audience
demographics.

Implementing this endpoint requires the Facebook OAuth flow to request
`pages_show_list`, `pages_read_engagement`, and `read_insights`, then allow the
creator to select a managed Page. The Meta app must include the Render
hostname in **App Domains** and the exact HTTPS callback in **Valid OAuth
Redirect URIs**. Some Page Insights metrics are version-dependent or
deprecated and may be returned as empty or unavailable.

### `POST /analytics/accounts/{account_id}/snapshots`

Stores a metric observation for an account owned by the current user. At least one metric must be supplied; values must be non-negative integers.

**Headers:** `Authorization: Bearer <access_token>`.

**Request body**

```json
{"follower_count": 1200, "view_count": 5300}
```

Either field may be `null` or omitted, but not both.

**201 response**

```json
{
  "id": 101,
  "social_account_id": 31,
  "follower_count": 1200,
  "view_count": 5300,
  "recorded_at": "2026-10-08T12:00:00Z"
}
```

**Errors:** `404` account not found/owned; `422` no metric supplied or invalid value.

### `GET /analytics/accounts/{account_id}/snapshots`

Lists recorded metric snapshots for an account owned by the current user, ordered by recording time.

**Headers:** `Authorization: Bearer <access_token>`.

**200 response:** array of metric snapshot objects as shown above.

**Errors:** `404` account not found/owned.

## Current implementation limits

- There is no background worker that dispatches scheduled content; scheduling currently persists calendar entries only.
- `POST /content/{content_id}/publish` intentionally returns `501` until Facebook and YouTube write scopes and upload implementations are added.
- Follower snapshots are manually posted; platform integrations do not currently retrieve audience size.
- Bearer access tokens identify authenticated users.
