from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.session import get_db
from app.models.profile import CompanyProfile, CreatorProfile
from app.models.user import RoleEnum, User
from app.schemas.auth import CompanySignupRequest, CreatorSignupRequest, LoginRequest
from app.schemas.user import AuthUserRead, CompanyProfileRead, CreatorProfileRead, UserRead


router = APIRouter()


def build_auth_response(user: User) -> AuthUserRead:
    profile = user.creator_profile if user.role == RoleEnum.creator else user.company_profile
    if user.role == RoleEnum.creator and profile is not None:
        profile_data = CreatorProfileRead.model_validate(profile)
    elif user.role == RoleEnum.company and profile is not None:
        profile_data = CompanyProfileRead.model_validate(profile)
    else:
        profile_data = None

    return AuthUserRead(user=UserRead.model_validate(user), profile=profile_data)


@router.post("/register/creator", response_model=AuthUserRead, status_code=status.HTTP_201_CREATED)
def register_creator(payload: CreatorSignupRequest, db: Session = Depends(get_db)) -> AuthUserRead:
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(email=payload.email, hashed_password=get_password_hash(payload.password), role=RoleEnum.creator)
    creator_profile = CreatorProfile(
        user=user,
        full_name=payload.full_name,
        city_state=payload.city_state,
        country=payload.country,
        creator_category=payload.creator_category,
        content_experience=payload.content_experience,
        content_interests=payload.content_interests,
        persona_goal=payload.persona_goal,
        profile_pic=payload.profile_pic,
        purposes=payload.purposes,
    )

    db.add(user)
    db.add(creator_profile)
    db.commit()
    db.refresh(user)
    return build_auth_response(user)


@router.post("/register/company", response_model=AuthUserRead, status_code=status.HTTP_201_CREATED)
def register_company(payload: CompanySignupRequest, db: Session = Depends(get_db)) -> AuthUserRead:
    existing_user = db.query(User).filter(User.email == payload.business_email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(email=payload.business_email, hashed_password=get_password_hash(payload.password), role=RoleEnum.company)
    company_profile = CompanyProfile(
        user=user,
        business_email=payload.business_email,
        company_name=payload.company_name,
        company_size=payload.company_size,
        company_website=payload.company_website,
        company_description=payload.company_description,
        company_logo=payload.company_logo,
        city_state=payload.city_state,
        country=payload.country,
        industry=payload.industry,
        marketing_goal=payload.marketing_goal,
        creator_categories=payload.creator_categories,
        platforms=payload.platforms,
        purposes=payload.purposes,
        additional_notes=payload.additional_notes,
    )

    db.add(user)
    db.add(company_profile)
    db.commit()
    db.refresh(user)
    return build_auth_response(user)


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict:
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    access_token = create_access_token(subject=user.email)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": build_auth_response(user),
    }


@router.get("/me", response_model=AuthUserRead)
def read_me(current_user: User = Depends(get_current_user)) -> AuthUserRead:
    return build_auth_response(current_user)
