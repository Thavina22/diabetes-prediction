"""Feature flags — defaults and deterministic percentage rollout."""

import asyncio

from services import feature_flags as ff


def test_defaults_are_exposed():
    flags = {flag["key"] for flag in asyncio.run(ff.get_all_flags())}
    assert {"ensemble_model", "pdf_export", "fhir_export", "device_sync"} <= flags


def test_disabled_flag_is_off():
    assert ff.evaluate({"enabled": False, "rollout_percentage": 100}, "user-1") is False


def test_full_rollout_is_on():
    assert ff.evaluate({"enabled": True, "rollout_percentage": 100}, "user-1") is True


def test_zero_rollout_is_off_for_known_user():
    assert ff.evaluate({"enabled": True, "rollout_percentage": 0}, "user-1") is False


def test_rollout_without_user_is_on():
    # No user to bucket -> default to on once the flag is enabled.
    assert ff.evaluate({"enabled": True, "rollout_percentage": 10}, None) is True


def test_rollout_is_deterministic():
    flag = {"enabled": True, "rollout_percentage": 50}
    first = ff.evaluate(flag, "user-abc")
    assert all(ff.evaluate(flag, "user-abc") == first for _ in range(10))


def test_rollout_splits_users():
    flag = {"enabled": True, "rollout_percentage": 50}
    on = sum(ff.evaluate(flag, f"user-{i}") for i in range(200))
    assert 0 < on < 200, "50% rollout should not be all-on or all-off"
