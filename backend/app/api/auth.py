from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from datetime import datetime, timedelta, timezone
import logging

from app.database import get_db
from app.models.admin_user import AdminUser
from app.schemas.auth import LoginRequest, AdminResponse, LoginResponse
from app.schemas.common import MessageResponse
from app.auth.security import verify_password, hash_password, create_access_token, get_current_admin
from app.auth.middleware import limiter
from app.services.audit_service import log_audit
from app.config import get_settings

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)


@router.post("/login", response_model=LoginResponse)
@limiter.limit(f"{settings.LOGIN_MAX_ATTEMPTS}/{settings.LOGIN_LOCKOUT_MINUTES}minutes")
def login(
    request: Request,
    response: Response,
    login_data: LoginRequest,
    db: Session = Depends(get_db),
):
    login_identifier = login_data.username.strip().lower()
    user = (
        db.query(AdminUser)
        .filter(
            or_(
                func.lower(AdminUser.username) == login_identifier,
                func.lower(AdminUser.email) == login_identifier,
            )
        )
        .first()
    )

    if not user:
        log_audit(
            db, "LOGIN_FAILED", "AdminUser", None,
            {"username": login_data.username, "reason": "user_not_found"},
            getattr(request.client, "host", None),
        )
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Check lockout
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        remaining = (user.locked_until - datetime.now(timezone.utc)).seconds
        log_audit(
            db, "LOGIN_FAILED", "AdminUser", user.id,
            {"username": user.username, "reason": "account_locked"},
            getattr(request.client, "host", None),
        )
        raise HTTPException(
            status_code=403,
            detail=f"Account is temporarily locked. Try again in {remaining // 60 + 1} minutes.",
        )

    # Verify password
    if not verify_password(login_data.password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.LOGIN_MAX_ATTEMPTS:
            user.locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=settings.LOGIN_LOCKOUT_MINUTES
            )
            logger.warning(f"Admin account locked after {user.failed_login_attempts} failed attempts")
        db.commit()
        log_audit(
            db, "LOGIN_FAILED", "AdminUser", user.id,
            {"username": user.username, "reason": "wrong_password", "attempts": user.failed_login_attempts},
            getattr(request.client, "host", None),
        )
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Successful login — upgrade plaintext hash to bcrypt if needed
    if not user.password_hash.startswith(("$2a$", "$2b$", "$2y$")):
        user.password_hash = hash_password(login_data.password)

    # Successful login — reset counters
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(data={"sub": user.username})
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        samesite="none" if settings.APP_ENV == "production" else "lax",
        secure=True if settings.APP_ENV == "production" else False,
        max_age=settings.JWT_EXPIRY_HOURS * 3600,
    )

    log_audit(
        db, "LOGIN_SUCCESS", "AdminUser", user.id,
        {"username": user.username},
        getattr(request.client, "host", None),
    )
    logger.info(f"Admin login successful: {user.username}")
    return LoginResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        last_login_at=user.last_login_at,
        access_token=access_token,
        token_type="bearer",
    )


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    response.delete_cookie(
        key="access_token",
        samesite="none" if settings.APP_ENV == "production" else "lax",
        secure=True if settings.APP_ENV == "production" else False,
    )
    log_audit(
        db, "LOGOUT", "AdminUser", current_admin.id,
        {"username": current_admin.username},
        getattr(request.client, "host", None),
    )
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=AdminResponse)
def get_me(current_admin: AdminUser = Depends(get_current_admin)):
    return current_admin
