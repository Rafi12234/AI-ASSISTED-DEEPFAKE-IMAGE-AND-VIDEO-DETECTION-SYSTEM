from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.core import User
from app.schemas.auth import LoginRequest, MeResponse, RegisterRequest, TokenResponse, UserResponse
from app.services.auth import create_access_token, hash_password, verify_password


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    existing_user_result = await db.execute(
        select(User).where(User.email == payload.email.lower())
    )
    existing_user = existing_user_result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role="user",
        is_active=True,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )

    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    user_result = await db.execute(
        select(User).where(User.email == payload.email.lower())
    )
    user = user_result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )

    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=MeResponse)
async def me(
    current_user: User = Depends(get_current_user),
):
    return MeResponse(
        user=UserResponse.model_validate(current_user)
    )