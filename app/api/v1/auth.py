import json

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.social_accounts import current_user_id
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.registration_profile import Company, Creator
from app.models.user import User
from app.schemas.auth import AuthResponse, CompanyRegisterRequest, CreatorRegisterRequest, LoginRequest, RegisterRequest
from app.services.media_upload_service import MediaUploadError, MediaUploadService

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
async def register_creator(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    content_type = request.headers.get("content-type", "")
    profile_file: UploadFile | None = None
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        values = CreatorRegisterRequest(
            email=form.get("email"),
            password=form.get("password"),
            fullName=form.get("fullName"),
            cityState=form.get("cityState"),
            country=form.get("country"),
            creatorCategory=form.get("creatorCategory"),
            contentExperience=form.get("contentExperience"),
            contentInterests=_form_list(form, "contentInterests"),
            personalGoal=form.get("personalGoal", form.get("personaGoal")),
            purposes=_form_list(form, "purposes"),
        )
        uploaded_file = form.get("profilePic")
        if uploaded_file is not None and not isinstance(uploaded_file, UploadFile):
            raise HTTPException(status_code=422, detail="profilePic must be an image file")
        profile_file = uploaded_file
    else:
        values = CreatorRegisterRequest.model_validate(await request.json())

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
        purposes=values.purposes,
    )
    db.add(user)
    await db.flush()

    if profile_file is not None:
        try:
            user.creator.profile_pic = (
                await MediaUploadService(get_settings()).upload_profile_image(profile_file, user.id)
            )["profile_pic"]
        except MediaUploadError as exc:
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        finally:
            await profile_file.close()

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered") from exc
    await db.refresh(user)
    return _auth_response(user)


def _form_list(form, name: str) -> list[str]:
    values = form.getlist(name)
    if len(values) == 1 and isinstance(values[0], str):
        try:
            parsed = json.loads(values[0])
        except json.JSONDecodeError:
            return [values[0]]
        if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
            return parsed
    return [value for value in values if isinstance(value, str)]


@router.post("/me/profile-picture")
async def upload_profile_picture(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(current_user_id),
) -> dict[str, str]:
    creator = await db.scalar(select(Creator).where(Creator.user_id == user_id))
    if creator is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creator profile not found")

    try:
        result = await MediaUploadService(get_settings()).upload_profile_image(file, user_id)
    except MediaUploadError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    finally:
        await file.close()

    profile_url = result["profile_pic"]
    creator.profile_pic = profile_url
    await db.commit()
    return {"profile_pic": profile_url}


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
