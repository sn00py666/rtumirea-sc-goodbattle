from __future__ import annotations

import os
import sys
from pathlib import Path

# Make `app` importable when pytest is launched from the backend root.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Keep imports stable in tests for modules that read env at import time.
os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('JWT_ALGORITHM', 'HS256')
os.environ.setdefault('TOKEN_EXPIRATION_DAYS', '7')
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///./analytics-test.db')
