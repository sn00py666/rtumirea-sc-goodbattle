from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.access import is_admin_email
from app.auth import create_access_token, hash_password, verify_password
from app.database import get_async_session
from app.dependencies import get_current_user, SESSION_COOKIE_NAME
from app.models import User
from app.schemas import LoginRequest, RegisterRequest, UserResponse

router = APIRouter()


@router.post('/register', response_model=UserResponse, status_code=201)
async def register_user(request: RegisterRequest, response: Response, session: AsyncSession = Depends(get_async_session)) -> UserResponse:
    existing_user = (await session.exec(select(User).where(User.email == request.email))).first()
    if existing_user:
        raise HTTPException(status_code=409, detail='Email уже зарегистрирован!')

    new_user = User(
        email=request.email,
        is_admin=is_admin_email(request.email),
        username=request.username,
        password_hash=hash_password(request.password),
    )

    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    session_token = create_access_token({'user_id': new_user.id})
    response.set_cookie(SESSION_COOKIE_NAME, session_token, httponly=True, samesite='none', secure=True, path='/')

    return UserResponse(**new_user.model_dump())


@router.post('/login', response_model=UserResponse)
async def login_user(request: LoginRequest, response: Response, session: AsyncSession = Depends(get_async_session)) -> UserResponse:
    user = (await session.exec(select(User).where(User.email == request.email))).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail='Неверный email или пароль!')

    session_token = create_access_token({'user_id': user.id})
    response.set_cookie(SESSION_COOKIE_NAME, session_token, httponly=True, samesite='none', secure=True, path='/')

    return UserResponse(**user.model_dump())


@router.post('/logout')
async def logout_user(response: Response):
    response.delete_cookie(
        SESSION_COOKIE_NAME,
        path='/',
        secure=True,
        samesite='none'
    )


@router.get('/me', response_model=UserResponse)
async def get_self_user(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(**user.model_dump())
