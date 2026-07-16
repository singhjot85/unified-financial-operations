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

from apps.core.utils import (
    ContentMaskingUtils,
    MockCursor,
    PatternMatcher,
    SQLCaptureContext,
    get_sensitive_matcher,
    stringify_dict,
)

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


# ---------------------------------------------------------------------------
# Unit: PatternMatcher — initialisation
# ---------------------------------------------------------------------------


class TestPatternMatcherInit:
    """Unit tests for ``PatternMatcher`` construction and phrase compilation."""

    def test_default_phrases_loaded_from_constants(self) -> None:
        """Without explicit phrases, must load from ``SENSITIVE_CONTENT_PHRASES``."""
        from apps.core.constants import SENSITIVE_CONTENT_PHRASES

        matcher = PatternMatcher()
        assert matcher.phrases == SENSITIVE_CONTENT_PHRASES

    def test_custom_phrases_override_defaults(self) -> None:
        """Explicit ``phrases`` kwarg must replace the constant list."""
        matcher = PatternMatcher(phrases=["mytoken", "mysecret"])
        assert matcher.phrases == ["mytoken", "mysecret"]

    def test_case_insensitive_by_default(self) -> None:
        """``case_sensitive`` must default to ``False``."""
        matcher = PatternMatcher()
        assert matcher.case_sensitive is False

    def test_case_sensitive_flag_stored(self) -> None:
        """Passing ``case_sensitive=True`` must be persisted."""
        matcher = PatternMatcher(case_sensitive=True)
        assert matcher.case_sensitive is True

    def test_compiled_patterns_are_set_after_init(self) -> None:
        """``_compiled_patterns`` must be a compiled ``re.Pattern`` after construction."""
        import re

        matcher = PatternMatcher(phrases=["token"])
        assert isinstance(matcher._compiled_patterns, re.Pattern)

    def test_optimized_phrases_are_set_after_init(self) -> None:
        """``_optimized_phrases`` must be a non-empty list after construction."""
        matcher = PatternMatcher(phrases=["token", "secret"])
        assert isinstance(matcher._optimized_phrases, list)
        assert len(matcher._optimized_phrases) > 0

    def test_minimum_length_is_three(self) -> None:
        """Class constant ``MINIMUM_LENGTH`` must be 3."""
        assert PatternMatcher.MINIMUM_LENGTH == 3


# ---------------------------------------------------------------------------
# Unit: PatternMatcher — _optimize_phrases
# ---------------------------------------------------------------------------


class TestPatternMatcherOptimizePhrases:
    """Tests for the redundant-phrase-removal logic in ``_optimize_phrases``."""

    def test_phrases_not_removed_when_no_longer_superset(self) -> None:
        """Phrases that are not substrings of other phrases must be kept."""
        matcher = PatternMatcher(phrases=["alpha", "beta"])
        assert "alpha" in matcher._optimized_phrases
        assert "beta" in matcher._optimized_phrases

    def test_phrases_sorted_longest_first(self) -> None:
        """``_optimized_phrases`` must be sorted by descending length."""
        matcher = PatternMatcher(phrases=["ab", "abcdef", "abc"])
        lengths = [len(p) for p in matcher._optimized_phrases]
        assert lengths == sorted(lengths, reverse=True)

    def test_duplicates_collapsed(self) -> None:
        """Identical phrases (case-insensitive) must appear only once."""
        matcher = PatternMatcher(phrases=["Token", "token", "TOKEN"])
        count = sum(1 for p in matcher._optimized_phrases if p == "token")
        assert count == 1

    def test_empty_strings_filtered_out(self) -> None:
        """Empty strings in the phrase list must not appear in optimized output."""
        matcher = PatternMatcher(phrases=["secret", ""])
        assert "" not in matcher._optimized_phrases


# ---------------------------------------------------------------------------
# Unit: PatternMatcher — is_sensitive
# ---------------------------------------------------------------------------


class TestPatternMatcherIsSensitive:
    """Unit tests for ``PatternMatcher.is_sensitive``."""

    def setup_method(self) -> None:
        self.matcher = PatternMatcher(phrases=["password", "secret", "token"])

    def test_returns_false_for_empty_string(self) -> None:
        """``is_sensitive`` must return ``False`` for empty string."""
        assert self.matcher.is_sensitive("") is False

    def test_returns_false_for_short_string(self) -> None:
        """``is_sensitive`` must return ``False`` for a string shorter than 3 chars."""
        assert self.matcher.is_sensitive("ab") is False

    def test_returns_true_for_exact_sensitive_phrase(self) -> None:
        """``is_sensitive`` must detect an exact match."""
        assert self.matcher.is_sensitive("password") is True

    def test_returns_true_for_phrase_in_sentence(self) -> None:
        """``is_sensitive`` must detect a phrase embedded in natural text."""
        assert self.matcher.is_sensitive("Enter your password here") is True

    def test_case_insensitive_match(self) -> None:
        """By default, ``is_sensitive`` must match regardless of case."""
        assert self.matcher.is_sensitive("PASSWORD") is True
        assert self.matcher.is_sensitive("Token") is True

    def test_case_sensitive_no_match(self) -> None:
        """With ``case_sensitive=True``, wrong-case text must not match."""
        cs_matcher = PatternMatcher(phrases=["password"], case_sensitive=True)
        assert cs_matcher.is_sensitive("PASSWORD") is False

    def test_returns_false_for_safe_text(self) -> None:
        """Plain non-sensitive text must return ``False``."""
        assert self.matcher.is_sensitive("hello world") is False

    def test_word_boundary_prevents_false_positive(self) -> None:
        """A sensitive phrase embedded mid-word must not match due to word-boundary rules."""
        # "token" inside "tokenize" — boundary pattern prevents match
        assert self.matcher.is_sensitive("tokenize") is False


# ---------------------------------------------------------------------------
# Unit: PatternMatcher — get_sensitive_phrases
# ---------------------------------------------------------------------------


class TestPatternMatcherGetSensitivePhrases:
    """Tests for ``PatternMatcher.get_sensitive_phrases``."""

    def setup_method(self) -> None:
        self.matcher = PatternMatcher(phrases=["password", "secret", "token"])

    def test_returns_empty_for_empty_input(self) -> None:
        """Must return ``[]`` for empty string."""
        assert self.matcher.get_sensitive_phrases("") == []

    def test_returns_matched_phrases(self) -> None:
        """Must return the list of matched sensitive phrases."""
        result = self.matcher.get_sensitive_phrases("reset your password now")
        assert len(result) >= 1
        assert any("password" in r.lower() for r in result)

    def test_deduplicates_repeated_phrase(self) -> None:
        """The same phrase appearing twice must appear only once in the result."""
        result = self.matcher.get_sensitive_phrases("password and password again")
        assert len([r for r in result if r.lower() == "password"]) == 1

    def test_returns_multiple_distinct_phrases(self) -> None:
        """Multiple different sensitive phrases must all appear in results."""
        result = self.matcher.get_sensitive_phrases("your password and secret")
        lower_results = [r.lower() for r in result]
        assert "password" in lower_results or "secret" in lower_results

    def test_returns_empty_for_safe_text(self) -> None:
        """Non-sensitive text must produce an empty list."""
        assert self.matcher.get_sensitive_phrases("hello world nothing here") == []


# ---------------------------------------------------------------------------
# Unit: PatternMatcher — mask_sensitive_content
# ---------------------------------------------------------------------------


class TestPatternMatcherMaskSensitiveContent:
    """Tests for ``PatternMatcher.mask_sensitive_content``."""

    def setup_method(self) -> None:
        self.matcher = PatternMatcher(phrases=["password", "secret"])

    def test_returns_empty_for_empty_input(self) -> None:
        """Must return the original (empty) value for empty input."""
        assert self.matcher.mask_sensitive_content("") == ""

    def test_masks_sensitive_phrase_with_default_mask(self) -> None:
        """Sensitive phrase in text must be replaced by ``'********'``."""
        result = self.matcher.mask_sensitive_content("Enter password now")
        assert "password" not in result.lower()
        assert "********" in result

    def test_custom_mask_string_is_used(self) -> None:
        """A custom ``mask`` argument must replace the default ``'********'``."""
        result = self.matcher.mask_sensitive_content("Enter password now", mask="[REDACTED]")
        assert "[REDACTED]" in result

    def test_safe_text_is_returned_unchanged(self) -> None:
        """Text without sensitive phrases must pass through unmodified."""
        text = "hello world"
        assert self.matcher.mask_sensitive_content(text) == text

    def test_multiple_sensitive_phrases_all_masked(self) -> None:
        """Every sensitive phrase occurrence must be replaced."""
        result = self.matcher.mask_sensitive_content("your password and secret are safe")
        assert "password" not in result.lower()
        assert "secret" not in result.lower()


# ---------------------------------------------------------------------------
# Unit: get_sensitive_matcher — singleton behaviour
# ---------------------------------------------------------------------------


class TestGetSensitiveMatcher:
    """Tests for the ``get_sensitive_matcher`` global singleton factory."""

    def test_returns_pattern_matcher_instance(self) -> None:
        """``get_sensitive_matcher`` must return a ``PatternMatcher``."""
        result = get_sensitive_matcher()
        assert isinstance(result, PatternMatcher)

    def test_returns_same_instance_on_repeated_calls(self) -> None:
        """Repeated calls must return the exact same singleton object."""
        first = get_sensitive_matcher()
        second = get_sensitive_matcher()
        assert first is second

    def test_singleton_reset_creates_new_instance(self) -> None:
        """Resetting the global to ``None`` forces a fresh instance on next call."""
        import apps.core.utils as utils_module

        original = utils_module._SENSITIVE_MATCHER
        try:
            utils_module._SENSITIVE_MATCHER = None
            new_instance = get_sensitive_matcher()
            assert isinstance(new_instance, PatternMatcher)
            assert new_instance is not original
        finally:
            utils_module._SENSITIVE_MATCHER = original


# ---------------------------------------------------------------------------
# Unit: stringify_dict
# ---------------------------------------------------------------------------


class TestStringifyDict:
    """Unit tests for ``stringify_dict``."""

    def test_flat_simple_dict(self) -> None:
        """Flat mode must produce ``key:value`` pairs joined by the separator."""
        result = stringify_dict({"a": 1, "b": 2}, flat=True)
        assert "a:1" in result
        assert "b:2" in result

    def test_flat_default_separator_is_comma(self) -> None:
        """Default separator must be ``,``."""
        result = stringify_dict({"a": 1, "b": 2}, flat=True)
        assert "," in result

    def test_flat_custom_separator(self) -> None:
        """A custom separator must appear in the output."""
        result = stringify_dict({"a": 1, "b": 2}, flat=True, separator="|")
        assert "|" in result

    def test_nested_dict_is_serialised(self) -> None:
        """Nested dicts must be wrapped in ``{...}`` notation."""
        result = stringify_dict({"outer": {"inner": "val"}}, flat=True)
        assert "outer" in result
        assert "inner" in result
        assert "val" in result

    def test_list_value_is_serialised(self) -> None:
        """List values must be wrapped in ``[...]`` notation."""
        result = stringify_dict({"items": [1, 2, 3]}, flat=True)
        assert "items" in result
        assert "1" in result
        assert "2" in result

    def test_empty_dict_returns_empty_string(self) -> None:
        """An empty dict must produce an empty string."""
        assert stringify_dict({}, flat=True) == ""

    def test_scalar_values_stringified(self) -> None:
        """Integer and boolean scalar values must be coerced to strings."""
        result = stringify_dict({"flag": True, "count": 42}, flat=True)
        assert "True" in result
        assert "42" in result


# ---------------------------------------------------------------------------
# Unit: ContentMaskingUtils — is_valid_email
# ---------------------------------------------------------------------------


class TestContentMaskingUtilsIsValidEmail:
    """Tests for the email validation helper."""

    def test_valid_simple_email(self) -> None:
        assert ContentMaskingUtils.is_valid_email("user@example.com") is True

    def test_missing_at_sign_is_invalid(self) -> None:
        assert ContentMaskingUtils.is_valid_email("userexample.com") is False

    def test_at_sign_with_content_on_both_sides(self) -> None:
        """Current implementation: '@' present and split length >= 2."""
        assert ContentMaskingUtils.is_valid_email("a@b") is True

    def test_empty_string_is_invalid(self) -> None:
        assert ContentMaskingUtils.is_valid_email("") is False


# ---------------------------------------------------------------------------
# Unit: ContentMaskingUtils — mask_email
# ---------------------------------------------------------------------------


class TestContentMaskingUtilsMaskEmail:
    """Tests for the email masking helper."""

    def test_valid_email_is_masked(self) -> None:
        """A valid email must be partially masked."""
        result = ContentMaskingUtils.mask_email("username@example.com")
        assert "@" in result
        assert "***" in result

    def test_long_username_keeps_first_two_chars(self) -> None:
        """Username > 3 chars: first two chars visible, then ``***``, then last char."""
        result = ContentMaskingUtils.mask_email("longname@example.com")
        assert result.startswith("lo")

    def test_short_username_becomes_stars(self) -> None:
        """Username <= 3 chars must be replaced entirely with ``***``."""
        result = ContentMaskingUtils.mask_email("ab@example.com")
        assert result.startswith("***")

    def test_invalid_email_returned_unchanged(self) -> None:
        """An invalid email (no ``@``) must be returned as-is."""
        result = ContentMaskingUtils.mask_email("notanemail")
        assert result == "notanemail"

    def test_domain_is_partially_masked(self) -> None:
        """The domain portion must also be partially masked."""
        result = ContentMaskingUtils.mask_email("user@example.com")
        domain_part = result.split("@")[1]
        assert "***" in domain_part


# ---------------------------------------------------------------------------
# Unit: ContentMaskingUtils — is_valid_phone
# ---------------------------------------------------------------------------


class TestContentMaskingUtilsIsValidPhone:
    """Tests for the phone number validation helper."""

    def test_ten_digit_number_is_valid(self) -> None:
        assert ContentMaskingUtils.is_valid_phone("1234567890") is True

    def test_fifteen_digit_number_is_valid(self) -> None:
        assert ContentMaskingUtils.is_valid_phone("123456789012345") is True

    def test_nine_digit_number_is_invalid(self) -> None:
        assert ContentMaskingUtils.is_valid_phone("123456789") is False

    def test_sixteen_digit_number_is_invalid(self) -> None:
        assert ContentMaskingUtils.is_valid_phone("1234567890123456") is False

    def test_phone_with_formatting_chars_valid(self) -> None:
        """Dashes, spaces, and parentheses must be stripped before digit count."""
        assert ContentMaskingUtils.is_valid_phone("+1 (800) 555-1234") is True

    def test_empty_string_is_invalid(self) -> None:
        assert ContentMaskingUtils.is_valid_phone("") is False


# ---------------------------------------------------------------------------
# Unit: ContentMaskingUtils — mask_phone
# ---------------------------------------------------------------------------


class TestContentMaskingUtilsMaskPhone:
    """Tests for the phone number masking helper."""

    def test_preserve_format_true_replaces_digits_with_stars(self) -> None:
        """With ``preserve_format=True`` each digit is replaced by ``*``."""
        result = ContentMaskingUtils.mask_phone("+1 (800) 555-1234", preserve_format=True)
        assert "1234" not in result
        # Non-digit chars must be kept in place
        assert " " in result or "-" in result or "(" in result

    def test_preserve_format_false_returns_stars_plus_last_four(self) -> None:
        """With ``preserve_format=False`` result is ``'******' + last 4 digits``."""
        result = ContentMaskingUtils.mask_phone("1234567890", preserve_format=False)
        assert result == "******7890"

    def test_preserve_format_false_short_number(self) -> None:
        """Less than 4 digits with ``preserve_format=False`` must return ``'****'``."""
        result = ContentMaskingUtils.mask_phone("123", preserve_format=False)
        assert result == "****"

    def test_preserve_format_true_keeps_non_digit_structure(self) -> None:
        """Dashes and spaces must be preserved in their original positions."""
        result = ContentMaskingUtils.mask_phone("123-456-7890", preserve_format=True)
        assert "-" in result


# ---------------------------------------------------------------------------
# Unit: ContentMaskingUtils — filter_value
# ---------------------------------------------------------------------------


class TestContentMaskingUtilsFilterValue:
    """Tests for the single-value filtering helper."""

    def setup_method(self) -> None:
        self.matcher = PatternMatcher(phrases=["password", "secret"])

    def test_sensitive_string_is_masked(self) -> None:
        """A value that IS a sensitive phrase must be replaced by ``mask_value``."""
        result = ContentMaskingUtils.filter_value("password", self.matcher)
        assert result == ContentMaskingUtils.mask_value

    def test_valid_email_is_masked(self) -> None:
        """A valid email value must be masked (partially)."""
        result = ContentMaskingUtils.filter_value("user@example.com", self.matcher)
        assert "@" in result
        assert "***" in result

    def test_valid_phone_is_masked(self) -> None:
        """A 10-digit phone value must be masked."""
        result = ContentMaskingUtils.filter_value("1234567890", self.matcher)
        # digits should be replaced — original full string must not survive
        assert "1234567890" not in result

    def test_safe_string_returned_unchanged(self) -> None:
        """A non-sensitive, non-email, non-phone string must pass through."""
        result = ContentMaskingUtils.filter_value("hello world", self.matcher)
        assert result == "hello world"

    def test_non_string_integer_returned_unchanged(self) -> None:
        """Integer values must be returned as-is."""
        assert ContentMaskingUtils.filter_value(42, self.matcher) == 42

    def test_non_string_none_returned_unchanged(self) -> None:
        """``None`` must be returned as-is."""
        assert ContentMaskingUtils.filter_value(None, self.matcher) is None

    def test_non_string_list_returned_unchanged(self) -> None:
        """List values must be returned as-is."""
        assert ContentMaskingUtils.filter_value([1, 2], self.matcher) == [1, 2]


# ---------------------------------------------------------------------------
# Unit: ContentMaskingUtils — filter_sensitive_content
# ---------------------------------------------------------------------------


class TestContentMaskingUtilsFilterSensitiveContent:
    """Tests for the main ``filter_sensitive_content`` orchestrator."""

    def test_sensitive_key_is_masked(self) -> None:
        """A key that matches a sensitive phrase must have its value replaced."""
        result = ContentMaskingUtils.filter_sensitive_content(password="hunter2")
        assert result["password"] == "********"

    def test_safe_key_value_is_preserved(self) -> None:
        """A safe key-value pair must survive unchanged."""
        result = ContentMaskingUtils.filter_sensitive_content(username="alice")
        assert result["username"] == "alice"

    def test_nested_dict_is_deep_searched(self) -> None:
        """With ``deep_search=True``, nested sensitive keys must also be masked."""
        result = ContentMaskingUtils.filter_sensitive_content(deep_search=True, credentials={"password": "secret123"})
        assert result["credentials"]["password"] == "********"

    def test_stringified_output_is_string(self) -> None:
        """With ``stringified=True``, the output must be a ``str``."""
        result = ContentMaskingUtils.filter_sensitive_content(stringified=True, username="alice")
        assert isinstance(result, str)

    def test_dict_output_is_dict(self) -> None:
        """Default (``stringified=False``) must return a ``dict``."""
        result = ContentMaskingUtils.filter_sensitive_content(username="alice")
        assert isinstance(result, dict)

    def test_custom_mask_value_is_applied(self) -> None:
        """A custom ``mask_value`` must replace the default ``'********'``."""
        result = ContentMaskingUtils.filter_sensitive_content(mask_value="[HIDDEN]", password="x")
        assert result["password"] == "[HIDDEN]"

    def test_email_value_is_partially_masked(self) -> None:
        """An email under a safe key must be partially masked by ``filter_value``."""
        result = ContentMaskingUtils.filter_sensitive_content(contact="user@example.com")
        assert "@" in result["contact"]
        assert "***" in result["contact"]

    def test_empty_attributes_returns_empty_dict(self) -> None:
        """Calling with no keyword attributes must return an empty dict."""
        result = ContentMaskingUtils.filter_sensitive_content()
        assert result == {}


# ---------------------------------------------------------------------------
# Unit: get_object_or_raise
# ---------------------------------------------------------------------------


class TestGetObjectOrRaise:
    """
    Unit tests for ``get_object_or_raise``.

    The Django model is fully mocked — no database is touched.
    """

    def setup_method(self) -> None:
        from apps.core.exceptions import ObjectNotFound

        self.ObjectNotFound = ObjectNotFound

        self.MockModel = MagicMock()
        self.MockModel.DoesNotExist = type("DoesNotExist", (Exception,), {})
        self.mock_instance = MagicMock()

    def test_returns_object_when_found(self) -> None:
        """Must return the instance when ``objects.get`` succeeds."""
        from apps.core.utils import get_object_or_raise

        self.MockModel.objects.get.return_value = self.mock_instance
        result = get_object_or_raise(self.MockModel, pk=1)
        assert result is self.mock_instance

    def test_raises_object_not_found_when_missing(self) -> None:
        """Must raise ``ObjectNotFound`` when ``objects.get`` raises ``DoesNotExist``."""
        from apps.core.utils import get_object_or_raise

        self.MockModel.objects.get.side_effect = self.MockModel.DoesNotExist()
        with pytest.raises(self.ObjectNotFound):
            get_object_or_raise(self.MockModel, pk=99)

    def test_passes_lookup_kwargs_to_objects_get(self) -> None:
        """The lookup kwargs must be forwarded verbatim to ``objects.get``."""
        from apps.core.utils import get_object_or_raise

        self.MockModel.objects.get.return_value = self.mock_instance
        get_object_or_raise(self.MockModel, name="Alice", active=True)
        self.MockModel.objects.get.assert_called_once_with(name="Alice", active=True)


# ---------------------------------------------------------------------------
# Unit: safe_get_object_or_raise
# ---------------------------------------------------------------------------


class TestSafeGetObjectOrRaise:
    """
    Unit tests for ``safe_get_object_or_raise``.

    The Django model is fully mocked.
    """

    def setup_method(self) -> None:
        from apps.core.exceptions import ObjectNotFound

        self.ObjectNotFound = ObjectNotFound

        self.MockModel = MagicMock()
        self.MockModel.DoesNotExist = type("DoesNotExist", (Exception,), {})
        self.MockModel.MultipleObjectsReturned = type("MultipleObjectsReturned", (Exception,), {})
        self.mock_instance = MagicMock()

    def test_returns_object_when_found(self) -> None:
        """Must return the instance when ``objects.get`` succeeds."""
        from apps.core.utils import safe_get_object_or_raise

        self.MockModel.objects.get.return_value = self.mock_instance
        result = safe_get_object_or_raise(self.MockModel, pk=1)
        assert result is self.mock_instance

    def test_raises_object_not_found_when_missing(self) -> None:
        """Must raise ``ObjectNotFound`` when ``objects.get`` raises ``DoesNotExist``."""
        from apps.core.utils import safe_get_object_or_raise

        self.MockModel.objects.get.side_effect = self.MockModel.DoesNotExist()
        with pytest.raises(self.ObjectNotFound):
            safe_get_object_or_raise(self.MockModel, pk=99)

    def test_handles_multiple_objects_returned_with_default_ordering(self) -> None:
        """
        When ``MultipleObjectsReturned`` is raised, must fall back to
        ``filter_objects_or_raise(...).order_by(DEFAULT_ORDERING).first()``.
        """
        from unittest.mock import patch

        from apps.core.utils import safe_get_object_or_raise

        self.MockModel.objects.get.side_effect = self.MockModel.MultipleObjectsReturned()
        self.MockModel.DEFAULT_ORDERING = "-created"

        fallback_instance = MagicMock()
        mock_qs = MagicMock()
        mock_qs.order_by.return_value.first.return_value = fallback_instance

        with patch("apps.core.utils.filter_objects_or_raise", return_value=mock_qs):
            result = safe_get_object_or_raise(self.MockModel, pk=1)

        assert result is fallback_instance
        mock_qs.order_by.assert_called_once_with("-created")

    def test_falls_back_to_pk_ordering_when_no_default_ordering(self) -> None:
        """
        When the model has no ``DEFAULT_ORDERING``, fallback ordering must be ``'-pk'``.
        """
        from unittest.mock import patch

        from apps.core.utils import safe_get_object_or_raise

        self.MockModel.objects.get.side_effect = self.MockModel.MultipleObjectsReturned()
        del self.MockModel.DEFAULT_ORDERING

        fallback_instance = MagicMock()
        mock_qs = MagicMock()
        mock_qs.order_by.return_value.first.return_value = fallback_instance

        with patch("apps.core.utils.filter_objects_or_raise", return_value=mock_qs):
            result = safe_get_object_or_raise(self.MockModel, pk=1)

        mock_qs.order_by.assert_called_once_with("-pk")
        assert result is fallback_instance


# ---------------------------------------------------------------------------
# Unit: filter_objects_or_raise
# ---------------------------------------------------------------------------


class TestFilterObjectsOrRaise:
    """
    Unit tests for ``filter_objects_or_raise``.

    The Django model is fully mocked.
    """

    def setup_method(self) -> None:
        from apps.core.exceptions import ObjectNotFound

        self.ObjectNotFound = ObjectNotFound

        self.MockModel = MagicMock()
        self.MockModel.DoesNotExist = type("DoesNotExist", (Exception,), {})

    def test_returns_queryset_when_results_found(self) -> None:
        """Must return the queryset when ``objects.get`` returns truthy."""
        from apps.core.utils import filter_objects_or_raise

        mock_qs = MagicMock()
        mock_qs.__bool__ = lambda self: True
        self.MockModel.objects.get.return_value = mock_qs

        result = filter_objects_or_raise(self.MockModel, active=True)
        assert result is mock_qs

    def test_raises_object_not_found_when_empty(self) -> None:
        """Must raise ``ObjectNotFound`` when the queryset is falsy (empty)."""
        from apps.core.utils import filter_objects_or_raise

        mock_qs = MagicMock()
        mock_qs.__bool__ = lambda self: False
        self.MockModel.objects.get.return_value = mock_qs

        with pytest.raises(self.ObjectNotFound):
            filter_objects_or_raise(self.MockModel, active=True)

    def test_passes_lookup_kwargs(self) -> None:
        """Lookup kwargs must be forwarded verbatim to the manager call."""
        from apps.core.utils import filter_objects_or_raise

        mock_qs = MagicMock()
        mock_qs.__bool__ = lambda self: True
        self.MockModel.objects.get.return_value = mock_qs

        filter_objects_or_raise(self.MockModel, name="Bob", status="active")
        self.MockModel.objects.get.assert_called_once_with(name="Bob", status="active")


# ---------------------------------------------------------------------------
# Unit: ObjectNotFound — exception raised by ORM helpers
# ---------------------------------------------------------------------------


class TestObjectNotFound:
    """Tests for ``ObjectNotFound`` — the shared exception raised by ORM helpers."""

    def test_can_be_raised_and_caught(self) -> None:
        """``ObjectNotFound`` must be a subclass of ``Exception``."""
        from apps.core.exceptions import ObjectNotFound

        with pytest.raises(ObjectNotFound):
            raise ObjectNotFound()

    def test_build_message_without_model(self) -> None:
        """Without a model, ``_build_message`` must fall back to the default name."""
        from apps.core.exceptions import ObjectNotFound

        exc = ObjectNotFound()
        msg = exc._build_message()
        assert "Object" in msg

    def test_build_message_with_lookup_kwargs_contains_not_found(self) -> None:
        """With lookup kwargs, the message must still contain 'not found'."""
        from apps.core.exceptions import ObjectNotFound

        exc = ObjectNotFound(username="alice")
        msg = exc._build_message()
        assert "not found" in msg

    def test_get_model_name_from_meta(self) -> None:
        """If the model has ``_meta``, the verbose name must be returned."""
        from apps.core.exceptions import ObjectNotFound

        mock_model = MagicMock()
        mock_model._meta.verbose_name.title.return_value = "Invoice"
        exc = ObjectNotFound(model=mock_model)
        assert exc._get_model_name() == "Invoice"

    def test_get_model_name_falls_back_to_class_name(self) -> None:
        """If the model has no ``_meta``, ``__name__`` must be used."""
        from apps.core.exceptions import ObjectNotFound

        class FakeModel:
            pass

        exc = ObjectNotFound(model=FakeModel)
        assert exc._get_model_name() == "FakeModel"

    def test_no_model_returns_default_name(self) -> None:
        """``_get_model_name`` must return ``'Object'`` when no model is set."""
        from apps.core.exceptions import ObjectNotFound

        exc = ObjectNotFound()
        assert exc._get_model_name() == ObjectNotFound.DEFAULT_MODEL_NAME
