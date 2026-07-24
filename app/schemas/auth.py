from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserBase(BaseModel):
    id: int
    email: EmailStr
    role: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class CreatorSignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str = Field(alias="fullName")
    city_state: str = Field(alias="cityState")
    country: str
    creator_category: str = Field(alias="creatorCategory")
    content_experience: str = Field(alias="contentExperience")
    content_interests: list[str] = Field(alias="contentInterests")
    persona_goal: str | None = Field(default=None, alias="personaGoal")
    profile_pic: str | None = Field(default=None, alias="profilePic")
    purposes: list[str]

    model_config = ConfigDict(populate_by_name=True)


class CompanySignupRequest(BaseModel):
    business_email: EmailStr = Field(alias="businessEmail")
    password: str
    company_name: str = Field(alias="companyName")
    company_size: str = Field(alias="companySize")
    company_website: str = Field(alias="companyWebsite")
    company_description: str = Field(alias="companyDescription")
    company_logo: str | None = Field(default=None, alias="companyLogo")
    city_state: str = Field(alias="cityState")
    country: str
    industry: str
    marketing_goal: str = Field(alias="marketingGoal")
    creator_categories: list[str] = Field(alias="creatorCategories")
    platforms: list[str]
    purposes: list[str]
    additional_notes: str | None = Field(default=None, alias="additionalNotes")

    model_config = ConfigDict(populate_by_name=True)
