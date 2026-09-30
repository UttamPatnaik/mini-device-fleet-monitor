from datetime import datetime, timedelta, timezone

from src.service import compute_status


def test_offline_when_no_heartbeat():
    now = datetime(2026, 9, 30, 10, 0, 0, tzinfo=timezone.utc)
    assert compute_status(None, now) == "OFFLINE"


def test_online_at_exact_30s_boundary():
    now = datetime(2026, 9, 30, 10, 0, 0, tzinfo=timezone.utc)
    last = now - timedelta(seconds=30)
    assert compute_status(last, now) == "ONLINE"


def test_offline_just_past_30s():
    now = datetime(2026, 9, 30, 10, 0, 0, tzinfo=timezone.utc)
    last = now - timedelta(seconds=31)
    assert compute_status(last, now) == "OFFLINE"


def test_online_when_heartbeat_is_fresh():
    now = datetime(2026, 9, 30, 10, 0, 0, tzinfo=timezone.utc)
    last = now - timedelta(seconds=5)
    assert compute_status(last, now) == "ONLINE"