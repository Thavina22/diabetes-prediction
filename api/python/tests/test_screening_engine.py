"""Screening assembler — shared by the screening, export and third-party routes."""

from models.screening import ScreeningInput

from services.screening_engine import build_result


def test_build_result_contract(normal_input: ScreeningInput):
    result = build_result(normal_input, "user-123")
    assert result.user_id == "user-123"
    assert result.input == normal_input
    assert 0 <= result.health_score <= 100
    assert result.risk_category in {"low", "medium", "high", "very_high"}
    assert result.ml_result is not None
    assert result.followup_schedule.when


def test_high_risk_input_is_stratified_high(normal_input: ScreeningInput, high_risk_input: ScreeningInput):
    normal = build_result(normal_input, "u")
    risky = build_result(high_risk_input, "u")
    order = {"low": 0, "medium": 1, "high": 2, "very_high": 3}
    assert order[risky.risk_category] > order[normal.risk_category]
    assert risky.health_score < normal.health_score


def test_result_ids_are_unique(normal_input: ScreeningInput):
    assert build_result(normal_input, "u").id != build_result(normal_input, "u").id
