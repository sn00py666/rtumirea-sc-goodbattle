from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from jose import JWTError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth import decode_access_token
from app.database import get_async_session
from app.models import User

SESSION_COOKIE_NAME = 'session'
UNAUTHORIZED_MESSAGE = 'Не авторизован'


async def get_current_user(request: Request, session: AsyncSession = Depends(get_async_session)) -> User:
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_token:
        raise HTTPException(status_code=401, detail=UNAUTHORIZED_MESSAGE)

    try:
        token_payload = decode_access_token(session_token)
    except JWTError:
        raise HTTPException(status_code=401, detail=UNAUTHORIZED_MESSAGE)

    user_id = token_payload.get('user_id')
    if not user_id:
        raise HTTPException(status_code=401, detail=UNAUTHORIZED_MESSAGE)

    current_user = (await session.exec(select(User).where(User.id == user_id))).first()
    if not current_user:
        raise HTTPException(status_code=401, detail=UNAUTHORIZED_MESSAGE)

    return current_user


async def require_admin_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail='Нет доступа')
    return user
