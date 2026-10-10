from datetime import datetime, timezone

import pytest


@pytest.mark.unit
def test_frozen_time_fixture_is_deterministic(frozen_time):
    expected = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

    assert datetime.now(timezone.utc) == expected
