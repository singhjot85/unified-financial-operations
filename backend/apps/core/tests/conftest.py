from unittest import mock

import pytest

from apps.core.utils import SQLCaptureContext


@pytest.fixture(autouse=True)
def tenant_db(request):
    """
    Override the root ``tenant_db`` autouse fixture for the core test suite.

    Core tests are pure Python infrastructure — they test descriptors, metaclasses,
    and import resolution, none of which require a database connection.

    Tests that genuinely need DB access must opt in explicitly with
    ``@pytest.mark.django_db`` and request the ``db`` fixture directly.
    """
    if "db" in request.fixturenames:
        yield  # A test explicitly requested db — yield and let django handle it.
    else:
        yield  # No DB needed — skip the schema-context dance entirely.


@pytest.fixture
def capture_db_queries():
    """
    Fixture that captures all database queries.
    Returns a ``SQLCaptureContext`` object with captured queries.

    ## Usage:

    ```python
        def test_something(capture_db_queries):

            # Do something that would query the DB

            with capture_db_queries as capture:
                # Your code here

                # Assert no queries were made
                capture.assert_no_queries()

                # Or inspect captured queries
                assert len(capture.queries) == 1
            assert capture.queries[0]['operation'] == 'SELECT'
    ```
    """
    return SQLCaptureContext()


@pytest.fixture
def mock_db_execute():
    """
    Simpler fixture that just mocks DB execute without capturing.
    """
    from apps.core.utils import MockCursor

    mock_cursor = MockCursor()

    with mock.patch("django.db.backends.utils.CursorWrapper", return_value=mock_cursor):
        with mock.patch("django.db.backends.base.base.BaseDatabaseWrapper.cursor", return_value=mock_cursor):
            yield mock_cursor
