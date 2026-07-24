# API Contract

Base URL:

- Local: `http://127.0.0.1:8000`
- Version prefix: `/api/v1`

All authenticated endpoints use Bearer JWT in the `Authorization` header:

```http
Authorization: Bearer <access_token>
```

## 1) Root

### `GET /`

Health check / app status.

#### Response `200`

```json
{
  "message": "Sumo backend is running"
}
```

## 2) Auth Routes

### `POST /api/v1/auth/register/creator`

Registers a creator account and creator profile.

#### Request Body

```json
{
  "email": "creator@example.com",
  "password": "secret123",
  "fullName": "Uday Shah",
  "cityState": "Ahmedabad",
  "country": "India",
  "creatorCategory": "Gaming",
  "contentExperience": "Beginner",
  "contentInterests": ["Gadgets"],
  "personaGoal": "",
  "profilePic": "",
  "purposes": ["Discover sponsorship opportunities", "Schedule social media posts", "Track analytics"]
}
```

#### Response `201`

```json
{
  "user": {
    "id": 1,
    "email": "creator@example.com",
    "role": "creator",
    "is_active": true,
    "created_at": "2026-07-24T10:00:00Z"
  },
  "profile": {
    "full_name": "Uday Shah",
    "city_state": "Ahmedabad",
    "country": "India",
    "creator_category": "Gaming",
    "content_experience": "Beginner",
    "content_interests": ["Gadgets"],
    "persona_goal": "",
    "profile_pic": "",
    "purposes": ["Discover sponsorship opportunities", "Schedule social media posts", "Track analytics"],
    "created_at": "2026-07-24T10:00:00Z"
  }
}
```

#### Error Responses

- `400` if the email is already registered

---

### `POST /api/v1/auth/register/company`

Registers a company/brand account and company profile.

#### Request Body

```json
{
  "businessEmail": "info@letses.com",
  "password": "secret123",
  "companyName": "LA ENGINEERING & TECHNOLOGY SOLUTIONS",
  "companySize": "Small Business",
  "companyWebsite": "letses.com",
  "companyDescription": "we are leading startup providing environmental solutions",
  "companyLogo": "",
  "cityState": "ahmedabad",
  "country": "India",
  "industry": "Technology",
  "marketingGoal": "Brand Awareness",
  "creatorCategories": ["Technology"],
  "platforms": ["Instagram", "Facebook", "YouTube", "LinkedIn"],
  "purposes": ["Find Content Creators", "Launch Brand Campaigns", "Manage Social Media Presence"],
  "additionalNotes": ""
}
```

#### Response `201`

```json
{
  "user": {
    "id": 2,
    "email": "info@letses.com",
    "role": "company",
    "is_active": true,
    "created_at": "2026-07-24T10:00:00Z"
  },
  "profile": {
    "business_email": "info@letses.com",
    "company_name": "LA ENGINEERING & TECHNOLOGY SOLUTIONS",
    "company_size": "Small Business",
    "company_website": "letses.com",
    "company_description": "we are leading startup providing environmental solutions",
    "company_logo": "",
    "city_state": "ahmedabad",
    "country": "India",
    "industry": "Technology",
    "marketing_goal": "Brand Awareness",
    "creator_categories": ["Technology"],
    "platforms": ["Instagram", "Facebook", "YouTube", "LinkedIn"],
    "purposes": ["Find Content Creators", "Launch Brand Campaigns", "Manage Social Media Presence"],
    "additional_notes": "",
    "created_at": "2026-07-24T10:00:00Z"
  }
}
```

#### Error Responses

- `400` if the email is already registered

---

### `POST /api/v1/auth/login`

Logs in a creator or company user with email and password.

#### Request Body

```json
{
  "email": "creator@example.com",
  "password": "secret123"
}
```

#### Response `200`

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "user": {
      "id": 1,
      "email": "creator@example.com",
      "role": "creator",
      "is_active": true,
      "created_at": "2026-07-24T10:00:00Z"
    },
    "profile": {
      "full_name": "Uday Shah",
      "city_state": "Ahmedabad",
      "country": "India",
      "creator_category": "Gaming",
      "content_experience": "Beginner",
      "content_interests": ["Gadgets"],
      "persona_goal": "",
      "profile_pic": "",
      "purposes": ["Discover sponsorship opportunities", "Schedule social media posts", "Track analytics"],
      "created_at": "2026-07-24T10:00:00Z"
    }
  }
}
```

#### Error Responses

- `401` if the email or password is incorrect

---

### `GET /api/v1/auth/me`

Returns the currently authenticated user and their profile.

#### Headers

```http
Authorization: Bearer <access_token>
```

#### Response `200`

Same shape as the `user` object returned from login.

#### Error Responses

- `401` if the token is missing or invalid

## 3) Role-Based Dashboard Routes

### `GET /api/v1/auth/creator/dashboard`

Creator-only endpoint.

#### Headers

```http
Authorization: Bearer <access_token>
```

#### Response `200`

```json
{
  "message": "Welcome creator creator@example.com"
}
```

#### Error Responses

- `401` if unauthenticated
- `403` if the user is not a creator

---

### `GET /api/v1/auth/company/dashboard`

Company-only endpoint.

#### Headers

```http
Authorization: Bearer <access_token>
```

#### Response `200`

```json
{
  "message": "Welcome company user info@letses.com"
}
```

#### Error Responses

- `401` if unauthenticated
- `403` if the user is not a company user

## Notes

- Signup endpoints accept the exact field names from your screenshots through Pydantic aliases.
- `password` is required for both signup payloads so login can work.
- The backend currently stores profiles in PostgreSQL using SQLAlchemy models.
