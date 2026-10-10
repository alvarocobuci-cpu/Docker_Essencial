from unittest.mock import Mock

import pytest

from inventory import database


@pytest.mark.unit
def test_get_db_closes_session(monkeypatch):
    session = Mock()
    monkeypatch.setattr(
        database,
        "SessionLocal",
        Mock(return_value=session),
    )

    generator = database.get_db()
    assert next(generator) is session

    generator.close()

    session.close.assert_called_once_with()
