"""
Thes utils are common utils, that can be used by pytest based tests,
These are generalized helper's that help's writing clean and isolated tests.
"""

import typing
from unittest.mock import MagicMock, patch


class MockCursor:
    """Mock cursor that properly handles Django's expectations"""

    def __init__(self):
        self.queries = []
        self.rowcount = 0
        self.description = None
        self._fetch_data = []
        self._fetch_index = 0

    def execute(self, sql, params=None):
        """Mock execute that captures SQL and returns self"""
        operation = self._detect_operation(sql)
        self.queries.append(
            {
                "sql": sql,
                "params": params,
                "operation": operation,
            }
        )

        # For INSERT with RETURNING, simulate returning ID
        if operation == "INSERT" and "RETURNING" in sql.upper():
            self._fetch_data = [(1,)]  # Simulate returning ID 1
            self.rowcount = 1
        elif operation == "SELECT":
            # For SELECT, return empty result set by default
            self._fetch_data = []
            self.rowcount = 0
        else:
            self.rowcount = 1

        self._fetch_index = 0
        return self

    def _detect_operation(self, sql: str) -> str:
        """Detect SQL operation type"""
        sql_upper = sql.strip().upper()

        if sql_upper.startswith("SELECT"):
            return "SELECT"
        elif sql_upper.startswith("INSERT"):
            return "INSERT"
        elif sql_upper.startswith("UPDATE"):
            return "UPDATE"
        elif sql_upper.startswith("DELETE"):
            return "DELETE"
        elif sql_upper.startswith("CREATE"):
            return "CREATE"
        elif sql_upper.startswith("ALTER"):
            return "ALTER"
        elif sql_upper.startswith("DROP"):
            return "DROP"
        elif "SAVEPOINT" in sql_upper:
            return "SAVEPOINT"
        elif "RELEASE" in sql_upper:
            return "RELEASE"
        else:
            return "OTHER"

    def fetchone(self):
        """Mock fetchone - returns first row"""
        if self._fetch_index < len(self._fetch_data):
            result = self._fetch_data[self._fetch_index]
            self._fetch_index += 1
            return result
        return None

    def fetchall(self):
        """Mock fetchall - returns all rows"""
        result = self._fetch_data
        self._fetch_index = len(self._fetch_data)
        return result

    def fetchmany(self, size=None):
        """Mock fetchmany"""
        if size is None:
            size = 1
        end = min(self._fetch_index + size, len(self._fetch_data))
        result = self._fetch_data[self._fetch_index : end]
        self._fetch_index = end
        return result

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class SQLCaptureContext:
    """
    Context manager to capture SQL queries

    ## Usage:

    ```pytho
        def test_something():
            # Do something that would query the DB

            with SQLCaptureContext as capture:
                # Your code here
                ...

                # Assert no queries were made
                capture.assert_no_queries()

                # Or inspect captured queries
                assert len(capture.queries) == 1
            assert capture.queries[0]['operation'] == 'SELECT'
    ```
    """

    queries: list[dict[str, typing.Any]]
    _original_query: str

    OPERATION_SELECT = "SELECT"
    OPERATION_INSERT = "INSERT"
    OPERATION_UPDATE = "UPDATE"
    OPERATION_DELETE = "DELETE"
    OPERATION_UNKOWN = "OTHER"

    POSSIBLE_OPERATIONS = (OPERATION_DELETE, OPERATION_INSERT, OPERATION_SELECT, OPERATION_UNKOWN, OPERATION_UPDATE)

    def __init__(self):
        self.queries = []
        self._original_query = None

    def _create_mock_cursor(self):
        """Create a mock cursor that captures queries"""
        mock_cursor = MockCursor()
        # Store reference to capture queries
        self._mock_cursor = mock_cursor
        return mock_cursor

    def _create_mock_connection(self):
        """Create a mock connection with cursor method"""
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = self._create_mock_cursor()
        return mock_conn

    def __enter__(self):
        """Setup the mock"""
        # Patch the execute method
        mock_cursor = self._create_mock_cursor()

        self._patcher = patch("django.db.backends.utils.CursorWrapper", return_value=mock_cursor)
        self._patcher.start()

        # Also patch connection.cursor to return our mock
        self._connection_patcher = patch(
            "django.db.backends.base.base.BaseDatabaseWrapper.cursor", return_value=mock_cursor
        )
        self._connection_patcher.start()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup the mock"""
        self._patcher.stop()
        self._connection_patcher.stop()

    @property
    def captured_queries(self):
        """Get all captured queries"""
        if self._mock_cursor:
            return self._mock_cursor.queries
        return []

    def assert_no_queries(self):
        """Assert no queries were executed"""
        queries = self.captured_queries
        assert len(queries) == 0, f"Expected no queries, but found {len(queries)}"

    def assert_query_count(self, count: int):
        """Assert exact number of queries"""
        queries = self.captured_queries
        assert len(queries) == count, f"Expected {count} queries, found {len(queries)}"

    def get_queries_by_operation(self, operation: str):
        """Get all queries of a specific operation"""
        return [q for q in self.captured_queries if q["operation"] == operation.upper()]
