from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

load_dotenv()

logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO').upper(),
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
)

from app.code_runner import runner as code_runner  # noqa: E402
from app.database import initialize_database  # noqa: E402
from app.routes import analytics, auth, battles, languages, profile, rooms, tasks, ws  # noqa: E402

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info('Backend startup: initializing database')
    await initialize_database()
    warmup_pull_images = os.getenv('CODE_RUNNER_WARMUP_PULL_IMAGES', 'true').strip().lower() in {'1', 'true', 'yes', 'on'}

    if warmup_pull_images:
        logger.info('Backend startup: pre-pulling code runner images')
        try:
            await asyncio.to_thread(code_runner.ensure_ready)
            logger.info('Backend startup: code runner images are ready')
        except Exception as exc:
            logger.warning('Code runner warmup failed: %s', exc)
    else:
        logger.info('Backend startup: code runner image pre-pull is disabled')

    logger.info('Backend startup complete')
    yield
    logger.info('Backend shutdown')


app = FastAPI(lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(_, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={'detail': exc.errors()})


app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(auth.router, prefix='/api/auth')
app.include_router(profile.router, prefix='/api')
app.include_router(languages.router, prefix='/api')
app.include_router(tasks.router, prefix='/api')
app.include_router(rooms.router, prefix='/api')
app.include_router(battles.router, prefix='/api')
app.include_router(analytics.router, prefix='/api')
app.include_router(ws.router, prefix='/ws')
