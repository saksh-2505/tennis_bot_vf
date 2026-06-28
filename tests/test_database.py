from database import check_connection


def test_check_connection() -> None:
    result = check_connection()
    assert isinstance(result, bool)
