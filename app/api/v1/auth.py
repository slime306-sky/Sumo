from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.registration_profile import Company, Creator
from app.models.user import User
from app.schemas.auth import AuthResponse, CompanyRegisterRequest, CreatorRegisterRequest, LoginRequest, RegisterRequest

router = APIRouter(prefix="/auth", tags=["authentication"])


def _auth_response(user: User) -> AuthResponse:
    return AuthResponse(user_id=user.id, role=user.role, access_token=create_access_token(user.id, user.role))


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(values: RegisterRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    existing = await db.scalar(select(User).where(User.login_id == values.login_id))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Login ID is already registered")
    user = User(login_id=values.login_id, email=values.login_id, password_hash=hash_password(values.password), role=values.role)
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Login ID is already registered") from exc
    await db.refresh(user)
    return _auth_response(user)


async def _registered_email(email: str, db: AsyncSession) -> User | None:
    return await db.scalar(select(User).where(User.email == email))


@router.post("/register/creator", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register_creator(values: CreatorRegisterRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    if await _registered_email(values.email, db) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")
    user = User(login_id=values.email, email=values.email, password_hash=hash_password(values.password), role="creator")
    user.creator = Creator(
        full_name=values.full_name,
        city_state=values.city_state,
        country=values.country,
        creator_category=values.creator_category,
        content_experience=values.content_experience,
        content_interests=values.content_interests,
        personal_goal=values.personal_goal,
        profile_pic=values.profile_pic,
        purposes=values.purposes,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered") from exc
    await db.refresh(user)
    return _auth_response(user)


@router.post("/register/company", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register_company(values: CompanyRegisterRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    if await _registered_email(values.business_email, db) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")
    user = User(login_id=values.business_email, email=values.business_email, password_hash=hash_password(values.password), role="company")
    user.company = Company(
        company_name=values.company_name,
        company_size=values.company_size,
        company_website=values.company_website,
        company_description=values.company_description,
        company_logo=values.company_logo,
        city_state=values.city_state,
        country=values.country,
        industry=values.industry,
        marketing_goal=values.marketing_goal,
        creator_categories=values.creator_categories,
        platforms=values.platforms,
        purposes=values.purposes,
        additional_notes=values.additional_notes,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered") from exc
    await db.refresh(user)
    return _auth_response(user)


@router.post("/login", response_model=AuthResponse)
async def login(values: LoginRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    user = await db.scalar(select(User).where(User.login_id == values.login_id))
    if user is None or not verify_password(values.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid login ID or password", headers={"WWW-Authenticate": "Bearer"})
    return _auth_response(user)
