from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from openai import APIConnectionError, AuthenticationError, NotFoundError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.ai_analytics_service import ai_analytics_service
from app.analytics_service import (
    get_admin_platform_analytics,
    get_battle_detail_analytics,
    get_organizer_analytics,
    get_participant_analytics,
)
from app.database import get_async_session
from app.dependencies import get_current_user, require_admin_user
from app.models import RoomMember, User
from app.schemas import (
    AdminPlatformAnalyticsResponse,
    AiAnalyticsQueryRequest,
    AiAnalyticsQueryResponse,
    BattleDetailAnalyticsResponse,
    OrganizerAnalyticsResponse,
    ParticipantAnalyticsResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get('/analytics/participants/me', response_model=ParticipantAnalyticsResponse)
async def get_my_participant_analytics(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ParticipantAnalyticsResponse:
    return await get_participant_analytics(session, viewer=user, target_user_id=user.id)


@router.get('/analytics/participants/{user_id}', response_model=ParticipantAnalyticsResponse)
async def get_public_participant_analytics(
    user_id: str,
    viewer: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ParticipantAnalyticsResponse:
    try:
        return await get_participant_analytics(session, viewer=viewer, target_user_id=user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail='Пользователь не найден') from exc


@router.get('/analytics/battles/{battle_id}', response_model=BattleDetailAnalyticsResponse)
async def get_battle_analytics(
    battle_id: str,
    viewer: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> BattleDetailAnalyticsResponse:
    membership = (
        await session.exec(
            select(RoomMember).where(
                RoomMember.room_id == battle_id,
                RoomMember.user_id == viewer.id,
            )
        )
    ).first()

    if membership is None and not viewer.is_admin:
        raise HTTPException(status_code=403, detail='Нет доступа к баттлу')

    payload = await get_battle_detail_analytics(session, battle_id=battle_id)
    if payload is None:
        raise HTTPException(status_code=404, detail='Баттл не найден')

    return payload


@router.get('/analytics/organizer/me', response_model=OrganizerAnalyticsResponse)
async def get_my_organizer_analytics(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> OrganizerAnalyticsResponse:
    return await get_organizer_analytics(session, organizer_user_id=user.id)


@router.get('/analytics/admin/platform', response_model=AdminPlatformAnalyticsResponse)
async def get_platform_analytics(
    _admin_user: User = Depends(require_admin_user),
    session: AsyncSession = Depends(get_async_session),
) -> AdminPlatformAnalyticsResponse:
    return await get_admin_platform_analytics(session)


@router.post('/analytics/ai/query', response_model=AiAnalyticsQueryResponse)
async def run_ai_analytics_query(
    payload: AiAnalyticsQueryRequest,
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> AiAnalyticsQueryResponse:
    try:
        result = await ai_analytics_service.run_analytics_query(
            session=session,
            question=payload.question,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except NotFoundError as exc:
        detail = str(exc)
        if 'channel not found' in detail.lower():
            raise HTTPException(
                status_code=503,
                detail=(
                    'LLM-провайдер ответил: channel not found. '
                    'Проверьте, что ключ выдан в NekoCode Dashboard и доступен канал '
                    '(обычно alpha), а OPENAI_BASE_URL имеет вид '
                    'https://gateway.nekocode.app/<channel>/v1.'
                ),
            ) from exc
        raise HTTPException(status_code=503, detail='LLM endpoint not found') from exc
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=503,
            detail='Ошибка авторизации у LLM-провайдера. Проверьте OPENAI_API_KEY.',
        ) from exc
    except APIConnectionError as exc:
        raise HTTPException(
            status_code=503,
            detail='Ошибка подключения к LLM-провайдеру. Проверьте сеть и OPENAI_BASE_URL.',
        ) from exc
    except Exception as exc:
        logger.exception('AI analytics query failed')
        raise HTTPException(
            status_code=503,
            detail=(
                'Ошибка подключения к LLM-провайдеру. '
                'Проверьте OPENAI_BASE_URL, OPENAI_API_KEY и OPENAI_MODEL.'
            ),
        ) from exc

    return AiAnalyticsQueryResponse(**result)
