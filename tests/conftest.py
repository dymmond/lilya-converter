from __future__ import annotations

from pathlib import Path

FIXTURES_ROOT = Path(__file__).resolve().parent / "fixtures"
FASTAPI_FIXTURES = FIXTURES_ROOT / "fastapi"
GOLDEN_FIXTURES = FIXTURES_ROOT / "golden"


def fixture_source(name: str) -> Path:
    return FASTAPI_FIXTURES / name


def fixture_golden(name: str) -> Path:
    return GOLDEN_FIXTURES / name
