"""Verify user access tokens with the configured Supabase Auth server."""

import os
from typing import Annotated, Literal
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.profile import Profile

router = APIRouter(prefix="/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)
DB = Annotated[Session, Depends(get_db)]


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    role: Literal["employee", "technician"]


def unauthenticated():
    return HTTPException(401, "Sign in with a valid access token.", {"WWW-Authenticate": "Bearer"})


def verified_user_id(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> UUID:
    if credentials is None:
        raise unauthenticated()
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_PUBLISHABLE_KEY")
    if not url or not key:
        raise HTTPException(503, "Authentication is not configured.")
    try:
        response = request.app.state.auth_http.get(
            f"{url}/auth/v1/user",
            headers={"apikey": key, "Authorization": f"Bearer {credentials.credentials}"},
        )
        if response.status_code in {400, 401, 403}:
            raise unauthenticated()
        response.raise_for_status()
        user = response.json()
        if user.get("is_anonymous"):
            raise unauthenticated()
        return UUID(user["id"])
    except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise HTTPException(503, "Authentication service is unavailable.") from exc


def current_profile(user_id: Annotated[UUID, Depends(verified_user_id)], db: DB) -> Profile:
    profile = db.get(Profile, user_id)
    if profile is None:
        raise HTTPException(403, "Your account has no help desk profile.")
    return profile


CurrentProfile = Annotated[Profile, Depends(current_profile)]


def require_employee(profile: CurrentProfile) -> Profile:
    if profile.role != "employee":
        raise HTTPException(403, "Employee access is required.")
    return profile


def require_technician(profile: CurrentProfile) -> Profile:
    if profile.role != "technician":
        raise HTTPException(403, "Technician access is required.")
    return profile


@router.get("/me", response_model=ProfileRead)
def get_profile(profile: CurrentProfile):
    return profile
