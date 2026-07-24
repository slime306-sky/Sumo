from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class CreatorProfileRead(BaseModel):
    full_name: str
    city_state: str
    country: str
    creator_category: str
    content_experience: str
    content_interests: list[str]
    persona_goal: str | None
    profile_pic: str | None
    purposes: list[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompanyProfileRead(BaseModel):
    business_email: EmailStr
    company_name: str
    company_size: str
    company_website: str
    company_description: str
    company_logo: str | None
    city_state: str
    country: str
    industry: str
    marketing_goal: str
    creator_categories: list[str]
    platforms: list[str]
    purposes: list[str]
    additional_notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserRead(BaseModel):
    id: int
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthUserRead(BaseModel):
    user: UserRead
    profile: CreatorProfileRead | CompanyProfileRead | None
