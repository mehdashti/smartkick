# app/routers/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
import logging

from app.core.database import get_async_db_session
from app.core.config import settings # برای دریافت تنظیمات اگر لازم باشد
from app.core.security import decode_access_token
# --- استفاده از اسکیما و مدل جدید ---
from app.schemas.token import TokenData # برای payload دیکود شده
from app.models import User as DBUser # مدل SQLAlchemy
from app.schemas.user import UserPublic # اسکیمای Pydantic برای خروجی
# --- استفاده از سرویس کاربر ---
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

# --- OAuth2 Scheme ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)

# --- Common Dependencies ---
DBSession = Annotated[AsyncSession, Depends(get_async_db_session)]
OptionalToken = Annotated[str | None, Depends(oauth2_scheme)]

# --- Security Dependency Functions ---

async def get_current_user_from_token(
    token: OptionalToken,
    db: DBSession
) -> DBUser | None:
    if token is None:
        return None # بدون توکن، کاربر ناشناس است

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        logger.warning("Token decoding failed (invalid/expired).")
        raise credentials_exception

    username: str | None = payload.get("sub")
    if username is None:
        logger.error("Token payload missing 'sub' (username) claim.")
        raise credentials_exception

    user_service = UserService()
    user = await user_service.get_user_by_username(db, username=username)

    if user is None:
        logger.warning(f"User '{username}' from token not found in database.")
        raise credentials_exception

    logger.debug(f"Token validated successfully for user: {username}")
    return user

async def get_current_active_user(
    current_user: Annotated[DBUser | None, Depends(get_current_user_from_token)],
) -> DBUser:
    if current_user is None:
        logger.debug("Access denied: No valid user found from token.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not current_user.is_active:
        logger.warning(f"Access denied: User '{current_user.username}' is inactive.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    logger.debug(f"Authenticated active user: {current_user.username}")
    return current_user

async def require_admin_user(
    current_user: Annotated[DBUser, Depends(get_current_active_user)],
) -> DBUser:
    # Check if user has the 'admin' role
    if current_user.role != "admin":
         logger.warning(f"Access denied for user '{current_user.username}': Admin role required, but user has role '{current_user.role}'.")
         raise HTTPException(
             status_code=status.HTTP_403_FORBIDDEN,
             detail="Administrator privileges required",
         )
    logger.debug(f"Admin access granted for user: {current_user.username}")
    return current_user

# --- Typed Dependencies for Cleaner Router Signatures ---
CurrentUser = Annotated[DBUser, Depends(get_current_active_user)]
AdminUser = Annotated[DBUser, Depends(require_admin_user)]

# --- Dependency to return the public user model ---
async def get_current_active_user_public(
    current_user: CurrentUser
) -> UserPublic:
    """Returns the Pydantic UserPublic model safe for API responses"""
    # Use model_validate for Pydantic V2
    return UserPublic.model_validate(current_user)

CurrentUserPublic = Annotated[UserPublic, Depends(get_current_active_user_public)]