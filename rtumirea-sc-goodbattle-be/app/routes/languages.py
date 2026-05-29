from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_async_session
from app.models import Language
from app.schemas import LanguageResponse

router = APIRouter()


@router.get('/languages', response_model=List[LanguageResponse])
async def list_languages(session: AsyncSession = Depends(get_async_session)) -> List[LanguageResponse]:
    languages = (await session.exec(select(Language).order_by(Language.id))).all()
    return [LanguageResponse.model_validate(language.model_dump()) for language in languages]
