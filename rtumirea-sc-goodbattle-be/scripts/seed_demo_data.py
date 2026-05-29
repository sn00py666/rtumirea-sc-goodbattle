from __future__ import annotations

import asyncio
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _load_env_file() -> None:
    env_path = os.path.join(PROJECT_ROOT, '.env')
    if not os.path.exists(env_path):
        return

    with open(env_path, encoding='utf-8') as env_file:
        for line in env_file:
            raw_line = line.strip()
            if not raw_line or raw_line.startswith('#') or '=' not in raw_line:
                continue

            key, value = raw_line.split('=', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


_load_env_file()

from app.database import AsyncSessionFactory, initialize_database
from app.demo_seed import seed_demo_analytics_data


async def main() -> None:
    await initialize_database()
    async with AsyncSessionFactory() as session:
        created = await seed_demo_analytics_data(session)

    if created:
        print('Demo analytics dataset created')
    else:
        print('Demo analytics dataset already exists, nothing to do')


if __name__ == '__main__':
    asyncio.run(main())
