"""
Tests for ``core.utils`` infrastructure.

Coverage:
    - MockCursor            (unit)
    - SQLCaptureContext     (unit + integration)
    - ``capture_db_queries`` fixture (integration)
    - ``mock_db_execute``   fixture (integration)

Per the LLD, these tests are independent of any app state outside ``core``.
No real database access is performed; all DB interaction is mocked via
``SQLCaptureContext`` or the fixture equivalents.
"""

from __future__ import annotations

import typing
from unittest.mock import MagicMock

import django.db.backends.utils as _db_utils
import pytest

from apps.core.utils import MockCursor, SQLCaptureContext

# Capture the real CursorWrapper at import time — before any fixture patches it.
_ORIGINAL_CURSOR_WRAPPER = _db_utils.CursorWrapper

if typing.TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Unit: MockCursor
# ---------------------------------------------------------------------------


class TestMockCursor:
    """Unit tests for ``MockCursor`` — the low-level fake DB cursor."""

    def setup_method(self) -> None:
        """Fresh ``MockCursor`` instance for every test."""
        self.cursor = MockCursor()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def test_initial_state_is_empty(self) -> None:
        """On construction all accumulators must start empty / zero."""
        assert self.cursor.queries == []
        assert self.cursor.rowcount == 0
        assert self.cursor.description is None
        assert self.cursor._fetch_data == []
        assert self.cursor._fetch_index == 0

    # ------------------------------------------------------------------
    # _detect_operation
    # ------------------------------------------------------------------

    def test_detect_operation_select(self) -> None:
        """``_detect_operation`` must return ``'SELECT'`` for SELECT statements."""
        assert self.cursor._detect_operation("SELECT * FROM foo") == "SELECT"

    def test_detect_operation_insert(self) -> None:
        """``_detect_operation`` must return ``'INSERT'`` for INSERT statements."""
        assert self.cursor._detect_operation("INSERT INTO foo VALUES (1)") == "INSERT"

    def test_detect_operation_update(self) -> None:
        """``_detect_operation`` must return ``'UPDATE'`` for UPDATE statements."""
        assert self.cursor._detect_operation("UPDATE foo SET bar=1") == "UPDATE"

    def test_detect_operation_delete(self) -> None:
        """``_detect_operation`` must return ``'DELETE'`` for DELETE statements."""
        assert self.cursor._detect_operation("DELETE FROM foo WHERE id=1") == "DELETE"

    def test_detect_operation_create(self) -> None:
        """``_detect_operation`` must return ``'CREATE'`` for CREATE statements."""
        assert self.cursor._detect_operation("CREATE TABLE foo (id INT)") == "CREATE"

    def test_detect_operation_alter(self) -> None:
        """``_detect_operation`` must return ``'ALTER'`` for ALTER statements."""
        assert self.cursor._detect_operation("ALTER TABLE foo ADD COLUMN bar INT") == "ALTER"

    def test_detect_operation_drop(self) -> None:
        """``_detect_operation`` must return ``'DROP'`` for DROP statements."""
        assert self.cursor._detect_operation("DROP TABLE foo") == "DROP"

    def test_detect_operation_savepoint(self) -> None:
        """``_detect_operation`` must return ``'SAVEPOINT'`` when SAVEPOINT appears."""
        assert self.cursor._detect_operation("SAVEPOINT sp1") == "SAVEPOINT"

    def test_detect_operation_release(self) -> None:
        """
        ``_detect_operation`` checks for SAVEPOINT *before* RELEASE in the
        source, so ``'RELEASE SAVEPOINT sp1'`` (which contains the word
        SAVEPOINT) is classified as ``'SAVEPOINT'``.  A bare ``'RELEASE sp1'``
        string that does NOT contain SAVEPOINT hits the else-branch and returns
        ``'OTHER'`` because the source has no explicit RELEASE prefix check.

        This test documents the actual observable behaviour.
        """
        # Contains "SAVEPOINT" → caught by the SAVEPOINT branch first.
        assert self.cursor._detect_operation("RELEASE SAVEPOINT sp1") == "SAVEPOINT"

    def test_detect_operation_unknown_fallback(self) -> None:
        """``_detect_operation`` must return ``'OTHER'`` for unrecognised SQL."""
        assert self.cursor._detect_operation("VACUUM FULL foo") == "OTHER"

    def test_detect_operation_is_case_insensitive(self) -> None:
        """``_detect_operation`` must handle lower-case SQL keywords correctly."""
        assert self.cursor._detect_operation("select 1") == "SELECT"
        assert self.cursor._detect_operation("insert into foo values(1)") == "INSERT"

    def test_detect_operation_strips_leading_whitespace(self) -> None:
        """Leading whitespace must not confuse operation detection."""
        assert self.cursor._detect_operation("   SELECT 1") == "SELECT"

    # ------------------------------------------------------------------
    # execute — query accumulation
    # ------------------------------------------------------------------

    def test_execute_appends_query_record(self) -> None:
        """``execute`` must append a dict with ``sql``, ``params``, and ``operation``."""
        self.cursor.execute("SELECT 1", params=None)

        assert len(self.cursor.queries) == 1
        record = self.cursor.queries[0]
        assert record["sql"] == "SELECT 1"
        assert record["params"] is None
        assert record["operation"] == "SELECT"

    def test_execute_stores_params(self) -> None:
        """``execute`` must persist non-None params in the query record."""
        self.cursor.execute("SELECT * FROM foo WHERE id=%s", params=(42,))
        assert self.cursor.queries[0]["params"] == (42,)

    def test_execute_accumulates_multiple_queries(self) -> None:
        """Calling ``execute`` multiple times must grow the ``queries`` list."""
        self.cursor.execute("SELECT 1")
        self.cursor.execute("SELECT 2")
        self.cursor.execute("SELECT 3")
        assert len(self.cursor.queries) == 3

    def test_execute_returns_self(self) -> None:
        """``execute`` must return ``self`` to support method-chaining."""
        result = self.cursor.execute("SELECT 1")
        assert result is self.cursor

    # ------------------------------------------------------------------
    # execute — rowcount and fetch_data side-effects
    # ------------------------------------------------------------------

    def test_execute_select_sets_empty_fetch_data(self) -> None:
        """A SELECT statement must initialise ``_fetch_data`` to an empty list."""
        self.cursor.execute("SELECT * FROM foo")
        assert self.cursor._fetch_data == []
        assert self.cursor.rowcount == 0

    def test_execute_insert_with_returning_simulates_id(self) -> None:
        """INSERT … RETURNING must set ``_fetch_data`` to ``[(1,)]`` and ``rowcount`` to 1."""
        self.cursor.execute("INSERT INTO foo (bar) VALUES (%s) RETURNING id", params=(1,))
        assert self.cursor._fetch_data == [(1,)]
        assert self.cursor.rowcount == 1

    def test_execute_insert_without_returning_sets_rowcount_1(self) -> None:
        """Plain INSERT (no RETURNING) must set ``rowcount`` to 1."""
        self.cursor.execute("INSERT INTO foo (bar) VALUES (1)")
        assert self.cursor.rowcount == 1
        # _fetch_data only set for INSERT+RETURNING; without RETURNING it falls
        # through to the else branch which sets rowcount=1 but not _fetch_data
        assert self.cursor._fetch_data == []

    def test_execute_update_sets_rowcount_1(self) -> None:
        """An UPDATE must set ``rowcount`` to 1."""
        self.cursor.execute("UPDATE foo SET bar=1 WHERE id=1")
        assert self.cursor.rowcount == 1

    def test_execute_resets_fetch_index(self) -> None:
        """Each ``execute`` call must reset ``_fetch_index`` to 0."""
        self.cursor.execute("SELECT 1")
        self.cursor._fetch_index = 99  # manually advance
        self.cursor.execute("SELECT 2")
        assert self.cursor._fetch_index == 0

    # ------------------------------------------------------------------
    # fetchone
    # ------------------------------------------------------------------

    def test_fetchone_returns_none_when_no_data(self) -> None:
        """``fetchone`` must return ``None`` when ``_fetch_data`` is empty."""
        self.cursor.execute("SELECT * FROM foo")
        assert self.cursor.fetchone() is None

    def test_fetchone_returns_first_row(self) -> None:
        """``fetchone`` must return the first row from ``_fetch_data``."""
        self.cursor.execute("INSERT INTO foo RETURNING id")  # sets _fetch_data=[(1,)]
        result = self.cursor.fetchone()
        assert result == (1,)

    def test_fetchone_advances_index(self) -> None:
        """Successive ``fetchone`` calls must advance through the result set."""
        self.cursor._fetch_data = [(1,), (2,), (3,)]
        self.cursor._fetch_index = 0

        assert self.cursor.fetchone() == (1,)
        assert self.cursor.fetchone() == (2,)
        assert self.cursor.fetchone() == (3,)
        assert self.cursor.fetchone() is None

    # ------------------------------------------------------------------
    # fetchall
    # ------------------------------------------------------------------

    def test_fetchall_returns_empty_list_for_select(self) -> None:
        """``fetchall`` must return ``[]`` when no rows are in ``_fetch_data``."""
        self.cursor.execute("SELECT * FROM foo")
        assert self.cursor.fetchall() == []

    def test_fetchall_returns_all_rows(self) -> None:
        """``fetchall`` must return the entire ``_fetch_data`` list."""
        self.cursor._fetch_data = [(1,), (2,), (3,)]
        self.cursor._fetch_index = 0
        result = self.cursor.fetchall()
        assert result == [(1,), (2,), (3,)]

    def test_fetchall_exhausts_cursor(self) -> None:
        """After ``fetchall``, subsequent ``fetchone`` must return ``None``."""
        self.cursor._fetch_data = [(1,)]
        self.cursor._fetch_index = 0
        self.cursor.fetchall()
        assert self.cursor.fetchone() is None

    # ------------------------------------------------------------------
    # fetchmany
    # ------------------------------------------------------------------

    def test_fetchmany_default_size_1(self) -> None:
        """``fetchmany`` with no size argument must default to 1."""
        self.cursor._fetch_data = [(1,), (2,), (3,)]
        self.cursor._fetch_index = 0
        result = self.cursor.fetchmany()
        assert result == [(1,)]

    def test_fetchmany_with_explicit_size(self) -> None:
        """``fetchmany(2)`` must return at most 2 rows."""
        self.cursor._fetch_data = [(1,), (2,), (3,)]
        self.cursor._fetch_index = 0
        result = self.cursor.fetchmany(size=2)
        assert result == [(1,), (2,)]

    def test_fetchmany_clamps_to_available_data(self) -> None:
        """``fetchmany`` must not raise when requesting more rows than available."""
        self.cursor._fetch_data = [(1,)]
        self.cursor._fetch_index = 0
        result = self.cursor.fetchmany(size=10)
        assert result == [(1,)]

    def test_fetchmany_returns_empty_when_exhausted(self) -> None:
        """``fetchmany`` must return ``[]`` when the cursor is already exhausted."""
        self.cursor._fetch_data = [(1,)]
        self.cursor._fetch_index = 0
        self.cursor.fetchmany(size=1)
        assert self.cursor.fetchmany() == []

    # ------------------------------------------------------------------
    # Context-manager protocol
    # ------------------------------------------------------------------

    def test_context_manager_returns_self(self) -> None:
        """``MockCursor`` must work as a context manager, yielding itself."""
        with self.cursor as ctx:
            assert ctx is self.cursor

    def test_context_manager_does_not_suppress_exceptions(self) -> None:
        """``__exit__`` must not suppress exceptions raised inside the with-block."""
        with pytest.raises(ValueError):
            with self.cursor:
                raise ValueError("test error")


# ---------------------------------------------------------------------------
# Unit: SQLCaptureContext — class-level constants
# ---------------------------------------------------------------------------


class TestSQLCaptureContextConstants:
    """Validates the public operation-type constants on ``SQLCaptureContext``."""

    def test_select_constant(self) -> None:
        assert SQLCaptureContext.OPERATION_SELECT == "SELECT"

    def test_insert_constant(self) -> None:
        assert SQLCaptureContext.OPERATION_INSERT == "INSERT"

    def test_update_constant(self) -> None:
        assert SQLCaptureContext.OPERATION_UPDATE == "UPDATE"

    def test_delete_constant(self) -> None:
        assert SQLCaptureContext.OPERATION_DELETE == "DELETE"

    def test_unknown_constant(self) -> None:
        assert SQLCaptureContext.OPERATION_UNKOWN == "OTHER"

    def test_possible_operations_contains_all_constants(self) -> None:
        """``POSSIBLE_OPERATIONS`` must list all four named operations plus OTHER."""
        expected = {"SELECT", "INSERT", "UPDATE", "DELETE", "OTHER"}
        assert set(SQLCaptureContext.POSSIBLE_OPERATIONS) == expected


# ---------------------------------------------------------------------------
# Unit: SQLCaptureContext — initialisation
# ---------------------------------------------------------------------------


class TestSQLCaptureContextInit:
    """Tests for the ``__init__`` state of ``SQLCaptureContext``."""

    def test_initial_queries_list_is_empty(self) -> None:
        """A freshly constructed context must have an empty ``queries`` list."""
        ctx = SQLCaptureContext()
        assert ctx.queries == []

    def test_initial_original_query_is_none(self) -> None:
        """``_original_query`` must be ``None`` before the context is entered."""
        ctx = SQLCaptureContext()
        assert ctx._original_query is None


# ---------------------------------------------------------------------------
# Unit: SQLCaptureContext — internal cursor / connection factories
# ---------------------------------------------------------------------------


class TestSQLCaptureContextInternals:
    """Tests for the private helper methods that build mock objects."""

    def setup_method(self) -> None:
        self.ctx = SQLCaptureContext()

    def test_create_mock_cursor_returns_mock_cursor_instance(self) -> None:
        """``_create_mock_cursor`` must return a ``MockCursor``."""
        cursor = self.ctx._create_mock_cursor()
        assert isinstance(cursor, MockCursor)

    def test_create_mock_cursor_stores_reference(self) -> None:
        """``_create_mock_cursor`` must persist the cursor as ``_mock_cursor``."""
        cursor = self.ctx._create_mock_cursor()
        assert self.ctx._mock_cursor is cursor

    def test_create_mock_connection_returns_magic_mock(self) -> None:
        """``_create_mock_connection`` must return a ``MagicMock``."""
        self.ctx._create_mock_cursor()
        conn = self.ctx._create_mock_connection()
        assert isinstance(conn, MagicMock)

    def test_create_mock_connection_cursor_returns_mock_cursor(self) -> None:
        """The ``cursor()`` call on the mock connection must return the stored ``MockCursor``."""
        self.ctx._create_mock_cursor()
        conn = self.ctx._create_mock_connection()
        returned_cursor = conn.cursor()
        assert isinstance(returned_cursor, MockCursor)


# ---------------------------------------------------------------------------
# Unit: SQLCaptureContext — context-manager lifecycle
# ---------------------------------------------------------------------------


class TestSQLCaptureContextLifecycle:
    """Tests the ``__enter__`` / ``__exit__`` patching lifecycle."""

    def test_enter_returns_self(self) -> None:
        """``__enter__`` must return the ``SQLCaptureContext`` instance."""
        ctx = SQLCaptureContext()
        with ctx as result:
            assert result is ctx

    def test_exit_stops_patchers(self) -> None:
        """
        After the context exits both patchers must have been stopped.
        ``unittest.mock`` patchers do not raise on double-stop; instead we
        verify that the patched attribute has been restored to its original
        value, which is the observable side-effect of a successful stop.
        """
        import django.db.backends.utils as db_utils

        ctx = SQLCaptureContext()
        original = db_utils.CursorWrapper

        with ctx:
            pass

        # If both patchers stopped cleanly the attribute is back to original.
        assert db_utils.CursorWrapper is original

    def test_cursor_wrapper_is_patched_inside_context(self) -> None:
        """Inside the context ``django.db.backends.utils.CursorWrapper`` must be replaced."""
        import django.db.backends.utils as db_utils

        ctx = SQLCaptureContext()
        original = db_utils.CursorWrapper

        with ctx:
            assert db_utils.CursorWrapper is not original

        assert db_utils.CursorWrapper is original  # restored after exit

    def test_base_connection_cursor_is_patched_inside_context(self) -> None:
        """Inside the context ``BaseDatabaseWrapper.cursor`` must be replaced."""
        from django.db.backends.base.base import BaseDatabaseWrapper

        ctx = SQLCaptureContext()
        original_cursor = BaseDatabaseWrapper.cursor

        with ctx:
            assert BaseDatabaseWrapper.cursor is not original_cursor

        assert BaseDatabaseWrapper.cursor is original_cursor  # restored after exit


# ---------------------------------------------------------------------------
# Unit: SQLCaptureContext — captured_queries property
# ---------------------------------------------------------------------------


class TestSQLCaptureContextCapturedQueries:
    """Tests for the ``captured_queries`` property."""

    def test_captured_queries_returns_empty_before_any_execute(self) -> None:
        """``captured_queries`` must be empty if no SQL was executed."""
        ctx = SQLCaptureContext()
        with ctx:
            assert ctx.captured_queries == []

    def test_captured_queries_reflects_mock_cursor_queries(self) -> None:
        """``captured_queries`` must mirror ``_mock_cursor.queries``."""
        ctx = SQLCaptureContext()
        with ctx:
            ctx._mock_cursor.execute("SELECT 1")
            assert len(ctx.captured_queries) == 1
            assert ctx.captured_queries[0]["operation"] == "SELECT"

    def test_captured_queries_without_mock_cursor_raises(self) -> None:
        """
        Accessing ``captured_queries`` *outside* an active context (where
        ``_mock_cursor`` has not been set) raises ``AttributeError`` because
        the property unconditionally dereferences ``self._mock_cursor``.

        This test documents the current source behaviour so that any future
        change that adds a guard is caught and the test updated intentionally.
        """
        ctx = SQLCaptureContext()
        assert not hasattr(ctx, "_mock_cursor"), "pre-condition: _mock_cursor must not exist yet"
        with pytest.raises(AttributeError):
            _ = ctx.captured_queries


# ---------------------------------------------------------------------------
# Unit: SQLCaptureContext — assertion helpers
# ---------------------------------------------------------------------------


class TestSQLCaptureContextAssertions:
    """Unit tests for ``assert_no_queries`` and ``assert_query_count``."""

    def test_assert_no_queries_passes_when_empty(self) -> None:
        """``assert_no_queries`` must not raise when no queries have been captured."""
        ctx = SQLCaptureContext()
        with ctx:
            ctx.assert_no_queries()  # must not raise

    def test_assert_no_queries_fails_when_queries_exist(self) -> None:
        """``assert_no_queries`` must raise ``AssertionError`` when queries are present."""
        ctx = SQLCaptureContext()
        with ctx:
            ctx._mock_cursor.execute("SELECT 1")
            with pytest.raises(AssertionError, match="Expected no queries"):
                ctx.assert_no_queries()

    def test_assert_query_count_passes_with_correct_count(self) -> None:
        """``assert_query_count(n)`` must not raise when exactly n queries exist."""
        ctx = SQLCaptureContext()
        with ctx:
            ctx._mock_cursor.execute("SELECT 1")
            ctx._mock_cursor.execute("SELECT 2")
            ctx.assert_query_count(2)  # must not raise

    def test_assert_query_count_fails_on_mismatch(self) -> None:
        """``assert_query_count(n)`` must raise ``AssertionError`` when count differs."""
        ctx = SQLCaptureContext()
        with ctx:
            ctx._mock_cursor.execute("SELECT 1")
            with pytest.raises(AssertionError, match="Expected 3 queries"):
                ctx.assert_query_count(3)

    def test_assert_query_count_zero_passes_with_no_queries(self) -> None:
        """``assert_query_count(0)`` is equivalent to ``assert_no_queries``."""
        ctx = SQLCaptureContext()
        with ctx:
            ctx.assert_query_count(0)  # must not raise


# ---------------------------------------------------------------------------
# Unit: SQLCaptureContext — get_queries_by_operation
# ---------------------------------------------------------------------------


class TestSQLCaptureContextGetQueriesByOperation:
    """Tests for the ``get_queries_by_operation`` filter helper."""

    def setup_method(self) -> None:
        self.ctx = SQLCaptureContext()

    def test_returns_empty_list_when_no_queries(self) -> None:
        """Must return ``[]`` when nothing has been executed."""
        with self.ctx:
            result = self.ctx.get_queries_by_operation("SELECT")
            assert result == []

    def test_filters_select_queries(self) -> None:
        """Must return only SELECT records when filtering by 'SELECT'."""
        with self.ctx:
            self.ctx._mock_cursor.execute("SELECT 1")
            self.ctx._mock_cursor.execute("INSERT INTO foo VALUES (1)")
            selects = self.ctx.get_queries_by_operation("SELECT")
            assert len(selects) == 1
            assert selects[0]["operation"] == "SELECT"

    def test_filters_insert_queries(self) -> None:
        """Must return only INSERT records when filtering by 'INSERT'."""
        with self.ctx:
            self.ctx._mock_cursor.execute("SELECT 1")
            self.ctx._mock_cursor.execute("INSERT INTO foo VALUES (1)")
            inserts = self.ctx.get_queries_by_operation("INSERT")
            assert len(inserts) == 1
            assert inserts[0]["operation"] == "INSERT"

    def test_filters_update_queries(self) -> None:
        """Must return only UPDATE records when filtering by 'UPDATE'."""
        with self.ctx:
            self.ctx._mock_cursor.execute("SELECT 1")
            self.ctx._mock_cursor.execute("UPDATE foo SET bar=1 WHERE id=1")
            updates = self.ctx.get_queries_by_operation("UPDATE")
            assert len(updates) == 1
            assert updates[0]["operation"] == "UPDATE"

    def test_filters_delete_queries(self) -> None:
        """Must return only DELETE records when filtering by 'DELETE'."""
        with self.ctx:
            self.ctx._mock_cursor.execute("SELECT 1")
            self.ctx._mock_cursor.execute("DELETE FROM foo WHERE id=1")
            deletes = self.ctx.get_queries_by_operation("DELETE")
            assert len(deletes) == 1
            assert deletes[0]["operation"] == "DELETE"

    def test_filter_is_case_insensitive_on_argument(self) -> None:
        """The ``operation`` argument must be uppercased internally before filtering."""
        with self.ctx:
            self.ctx._mock_cursor.execute("SELECT 1")
            result_lower = self.ctx.get_queries_by_operation("select")
            result_upper = self.ctx.get_queries_by_operation("SELECT")
            assert len(result_lower) == len(result_upper) == 1

    def test_returns_multiple_matches(self) -> None:
        """When multiple queries share the same operation, all must be returned."""
        with self.ctx:
            self.ctx._mock_cursor.execute("SELECT 1")
            self.ctx._mock_cursor.execute("SELECT 2")
            self.ctx._mock_cursor.execute("SELECT 3")
            result = self.ctx.get_queries_by_operation("SELECT")
            assert len(result) == 3


# ---------------------------------------------------------------------------
# Integration: SQLCaptureContext used as context manager end-to-end
# ---------------------------------------------------------------------------


class TestSQLCaptureContextIntegration:
    """
    Integration-level tests that exercise ``SQLCaptureContext`` exactly as
    production tests would — entering the context, triggering (simulated) SQL,
    and asserting on the captured state.
    """

    def test_no_execute_yields_no_queries(self) -> None:
        """A context block with no SQL must produce zero captured queries."""
        with SQLCaptureContext() as capture:
            capture.assert_no_queries()

    def test_single_select_is_captured(self) -> None:
        """A single simulated SELECT must appear in ``captured_queries``."""
        with SQLCaptureContext() as capture:
            capture._mock_cursor.execute("SELECT * FROM test_table")
            capture.assert_query_count(1)

    def test_mixed_operations_are_captured_correctly(self) -> None:
        """Multiple different DML statements must all be captured with correct operations."""
        with SQLCaptureContext() as capture:
            capture._mock_cursor.execute("SELECT 1")
            capture._mock_cursor.execute("INSERT INTO foo VALUES (1)")
            capture._mock_cursor.execute("UPDATE foo SET x=2 WHERE id=1")
            capture._mock_cursor.execute("DELETE FROM foo WHERE id=1")

            capture.assert_query_count(4)
            assert len(capture.get_queries_by_operation("SELECT")) == 1
            assert len(capture.get_queries_by_operation("INSERT")) == 1
            assert len(capture.get_queries_by_operation("UPDATE")) == 1
            assert len(capture.get_queries_by_operation("DELETE")) == 1

    def test_captured_queries_accessible_after_context_exits(self) -> None:
        """Query records must still be readable after the context manager exits."""
        with SQLCaptureContext() as capture:
            capture._mock_cursor.execute("SELECT 1")

        # Outside the context — mock_cursor.queries still holds the data.
        assert len(capture._mock_cursor.queries) == 1

    def test_two_independent_contexts_do_not_share_state(self) -> None:
        """Two separate ``SQLCaptureContext`` instances must not share cursor state."""
        ctx1 = SQLCaptureContext()
        ctx2 = SQLCaptureContext()

        with ctx1 as c1:
            c1._mock_cursor.execute("SELECT 1")
            c1.assert_query_count(1)

        with ctx2 as c2:
            c2.assert_no_queries()

    def test_assert_no_queries_guards_pure_python_code(self) -> None:
        """
        Typical usage pattern: ensure a code path does NOT touch the database.
        This is the primary value proposition of ``SQLCaptureContext``.
        """

        def pure_python_function() -> int:
            """Does not touch the DB."""
            return 42

        with SQLCaptureContext() as capture:
            result = pure_python_function()
            capture.assert_no_queries()

        assert result == 42


# ---------------------------------------------------------------------------
# Integration: ``capture_db_queries`` fixture
# ---------------------------------------------------------------------------


class TestCaptureDbQueriesFixture:
    """
    Tests that verify the ``capture_db_queries`` fixture (defined in
    ``apps/core/tests/conftest.py``) correctly exposes a ``SQLCaptureContext``.
    """

    def test_fixture_returns_sql_capture_context_instance(self, capture_db_queries: SQLCaptureContext) -> None:
        """The fixture must yield a ``SQLCaptureContext`` object."""
        assert isinstance(capture_db_queries, SQLCaptureContext)

    def test_fixture_starts_with_empty_state(self, capture_db_queries: SQLCaptureContext) -> None:
        """The fixture object must be freshly initialised with an empty queries list."""
        assert capture_db_queries.queries == []
        assert capture_db_queries._original_query is None

    def test_fixture_used_as_context_manager(self, capture_db_queries: SQLCaptureContext) -> None:
        """The fixture value must be usable directly as a context manager."""
        with capture_db_queries as capture:
            assert capture is capture_db_queries

    def test_fixture_captures_simulated_query(self, capture_db_queries: SQLCaptureContext) -> None:
        """After simulating SQL, ``captured_queries`` must reflect the executed statement."""
        with capture_db_queries as capture:
            capture._mock_cursor.execute("SELECT 42")
            capture.assert_query_count(1)

    def test_fixture_assert_no_queries_passes_when_clean(self, capture_db_queries: SQLCaptureContext) -> None:
        """``assert_no_queries`` must not raise when the context block contains no SQL."""
        with capture_db_queries as capture:
            capture.assert_no_queries()  # must not raise

    def test_fixture_get_queries_by_operation_select(self, capture_db_queries: SQLCaptureContext) -> None:
        """``get_queries_by_operation`` must filter correctly when used via the fixture."""
        with capture_db_queries as capture:
            capture._mock_cursor.execute("SELECT 1")
            capture._mock_cursor.execute("INSERT INTO foo VALUES (1)")
            selects = capture.get_queries_by_operation(capture.OPERATION_SELECT)
            assert len(selects) == 1

    def test_fixture_patches_cursor_wrapper(self, capture_db_queries: SQLCaptureContext) -> None:
        """Inside the context the ``CursorWrapper`` target must be replaced."""
        import django.db.backends.utils as db_utils

        original = db_utils.CursorWrapper
        with capture_db_queries:
            assert db_utils.CursorWrapper is not original

    def test_fixture_restores_cursor_wrapper_after_exit(self, capture_db_queries: SQLCaptureContext) -> None:
        """After exiting the context the original ``CursorWrapper`` must be restored."""
        import django.db.backends.utils as db_utils

        original = db_utils.CursorWrapper
        with capture_db_queries:
            pass
        assert db_utils.CursorWrapper is original


# ---------------------------------------------------------------------------
# Integration: ``mock_db_execute`` fixture
# ---------------------------------------------------------------------------


class TestMockDbExecuteFixture:
    """
    Tests that verify the ``mock_db_execute`` fixture (defined in
    ``apps/core/tests/conftest.py``) exposes a ``MockCursor`` with
    both DB patches already active.
    """

    def test_fixture_returns_mock_cursor(self, mock_db_execute: MockCursor) -> None:
        """The fixture must yield a ``MockCursor`` instance."""
        assert isinstance(mock_db_execute, MockCursor)

    def test_fixture_cursor_starts_with_empty_queries(self, mock_db_execute: MockCursor) -> None:
        """The yielded cursor must begin with no captured queries."""
        assert mock_db_execute.queries == []

    def test_fixture_cursor_wrapper_is_patched(self, mock_db_execute: MockCursor) -> None:
        """
        While the fixture is active, ``django.db.backends.utils.CursorWrapper``
        must no longer be the original class — ``unittest.mock.patch`` replaces
        it with a ``MagicMock``.  We compare against the reference captured at
        module import time (``_ORIGINAL_CURSOR_WRAPPER``) so that this assertion
        works even when the test itself runs inside an already-patched context.
        """
        assert _db_utils.CursorWrapper is not _ORIGINAL_CURSOR_WRAPPER

    def test_fixture_cursor_captures_execute_calls(self, mock_db_execute: MockCursor) -> None:
        """Calling ``execute`` on the yielded cursor must accumulate query records."""
        mock_db_execute.execute("SELECT 1")
        assert len(mock_db_execute.queries) == 1
        assert mock_db_execute.queries[0]["operation"] == "SELECT"

    def test_fixture_cursor_fetchone_after_insert_returning(self, mock_db_execute: MockCursor) -> None:
        """After INSERT … RETURNING, ``fetchone`` must return the simulated ID."""
        mock_db_execute.execute("INSERT INTO foo (bar) VALUES (%s) RETURNING id", params=(1,))
        assert mock_db_execute.fetchone() == (1,)

    def test_fixture_rowcount_after_update(self, mock_db_execute: MockCursor) -> None:
        """After an UPDATE statement ``rowcount`` must be 1."""
        mock_db_execute.execute("UPDATE foo SET bar=1 WHERE id=1")
        assert mock_db_execute.rowcount == 1
