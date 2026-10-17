"""Shared pytest fixtures.

Tests run from ``api/python`` (see ``requirements-dev.txt``); this file also
puts that directory on ``sys.path`` so ``services`` / ``models`` import cleanly.
"""

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Must be set before config is imported anywhere so protected API routes and
# the stateless (no-database) mode are exercised as intended.
os.environ.setdefault("DEV_AUTH_BYPASS", "true")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DEV_USER_ID", "test-user")

from models.screening import ScreeningInput  # noqa: E402


@pytest.fixture
def normal_input() -> ScreeningInput:
    return ScreeningInput(
        glucose_mg_dl=90,
        glucose_type="fasting",
        sbp=118,
        dbp=76,
        height_cm=175,
        weight_kg=70,
        ldl_mg_dl=100,
        hdl_mg_dl=55,
        triglycerides_mg_dl=120,
        age=35,
        sex="M",
    )


@pytest.fixture
def high_risk_input() -> ScreeningInput:
    return ScreeningInput(
        glucose_mg_dl=180,
        glucose_type="fasting",
        sbp=150,
        dbp=95,
        height_cm=170,
        weight_kg=98,
        ldl_mg_dl=170,
        hdl_mg_dl=35,
        triglycerides_mg_dl=260,
        age=58,
        sex="M",
        family_history=True,
    )
