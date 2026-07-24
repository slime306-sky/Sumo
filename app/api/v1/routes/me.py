from fastapi import APIRouter, Depends

from app.api.deps import require_roles
from app.models.user import RoleEnum, User


router = APIRouter()


@router.get("/creator/dashboard")
def creator_dashboard(current_user: User = Depends(require_roles(RoleEnum.creator))) -> dict[str, str]:
    return {"message": f"Welcome creator {current_user.email}"}


@router.get("/company/dashboard")
def company_dashboard(current_user: User = Depends(require_roles(RoleEnum.company))) -> dict[str, str]:
    return {"message": f"Welcome company user {current_user.email}"}
