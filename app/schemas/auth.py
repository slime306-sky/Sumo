from typing import Annotated, Literal

from pydantic import BaseModel, Field


Role = Literal["creator", "brand", "company"]

Email = Annotated[str, Field(min_length=3, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")]


class CreatorRegisterRequest(BaseModel):
    email: Email
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(alias="fullName", min_length=1, max_length=150)
    city_state: str | None = Field(default=None, alias="cityState", max_length=150)
    country: str | None = Field(default=None, max_length=100)
    creator_category: str | None = Field(default=None, alias="creatorCategory", max_length=100)
    content_experience: str | None = Field(default=None, alias="contentExperience", max_length=100)
    content_interests: list[str] = Field(default_factory=list, alias="contentInterests")
    personal_goal: str | None = Field(default=None, alias="personalGoal")
    purposes: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid", "populate_by_name": True}


class CompanyRegisterRequest(BaseModel):
    business_email: Email = Field(alias="businessEmail")
    password: str = Field(min_length=8, max_length=128)
    company_name: str = Field(alias="companyName", min_length=1, max_length=200)
    company_size: str | None = Field(default=None, alias="companySize", max_length=50)
    company_website: str | None = Field(default=None, alias="companyWebsite")
    company_description: str | None = Field(default=None, alias="companyDescription")
    company_logo: str | None = Field(default=None, alias="companyLogo")
    city_state: str | None = Field(default=None, alias="cityState", max_length=150)
    country: str | None = Field(default=None, max_length=100)
    industry: str | None = Field(default=None, max_length=100)
    marketing_goal: str | None = Field(default=None, alias="marketingGoal")
    creator_categories: list[str] = Field(default_factory=list, alias="creatorCategories")
    platforms: list[str] = Field(default_factory=list)
    purposes: list[str] = Field(default_factory=list)
    additional_notes: str | None = Field(default=None, alias="additionalNotes")

    model_config = {"populate_by_name": True}


class RegisterRequest(BaseModel):
    login_id: str = Field(min_length=3, max_length=120, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)
    role: Role


class LoginRequest(BaseModel):
    login_id: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=128)


class AuthResponse(BaseModel):
    user_id: int
    role: Role
    access_token: str
    token_type: Literal["bearer"] = "bearer"
