from __future__ import annotations

import json
import logging
import re
import typing
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.conf import settings

from apps.core.constants import SENSITIVE_CONTENT_PHRASES
from apps.core.exceptions import InvalidTypeError, ObjectNotFound

if typing.TYPE_CHECKING:
    from django.db import models

LOGGER = logging.getLogger(__name__)

# Global singleton for the sensitive content matcher (lazy-initialised).
_SENSITIVE_MATCHER: "PatternMatcher | None" = None


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


class PatternMatcher:
    """
    High-performance regex-based sensitive content matcher.
    Uses pre-compiled patterns for O(1) matching.

    Attributes:
        phrases (list[str]): SENSITIVE_CONTENT_PHRASES pre-static value or can be passed at runtime.
        case_sensitive (bool): Case sensitive search or exact pattern search.
            False by default, bcz we want a case insensitive search, i.e. we want to find both ``Pass`` and ``pass`` for given phrase ``pass``
        _optimized_phrases (list[str]): Optimized phrases, after redundant phrase removal.
        MINIMUM_LENGTH (int): length of minmum string to scan, larger value gives performace,
            but smaller value's enforce harder search, Default is 3, not too high not too low.
    """

    phrases: list[str]
    _optimized_phrases: list[str]

    _compiled_patterns: re.Pattern
    case_sensitive: bool

    COMMON_PREFIXES = ["user_", "new_", "old_", "master_", "confirm_", "client_"]
    COMMON_SUFFIXES = ["_key", "_token", "_secret"]

    MINIMUM_LENGTH: int = 3

    def __init__(self, phrases: list[str] = None, case_sensitive: bool = False):
        """
        Args:
            phrases (list[str], optional): SENSITIVE_CONTENT_PHRASES pre-static value or can be passed at runtime.
            case_sensitive (bool, optional): Case sensitive search or exact pattern search.
                False by default, bcz we want a case insensitive search, i.e. we want to find both ``Pass`` and ``pass`` for given phrase ``pass``
        """
        self.phrases = phrases or SENSITIVE_CONTENT_PHRASES
        self.case_sensitive = case_sensitive
        self._compiled_patterns = None
        self._optimized_phrases = None
        self._compile_patterns()

    def _optimize_phrases(self) -> list[str]:
        """
        Remove redundant phrases.
        If 'password' is present, remove 'pass' to avoid false positives.
        """
        phrases = set(self.phrases)
        phrases = {p.lower() for p in phrases if p}

        to_remove = set()
        for phrase in phrases:
            for other in phrases:
                if phrase != other and phrase in other:
                    # If phrase is a substring of another, keep the longer one
                    # unless the longer one is just adding common prefixes/suffixes
                    if len(other) - len(phrase) > 3:
                        # Check if it's just adding common prefixes/suffixes
                        common_prefixes = self.COMMON_PREFIXES
                        common_suffixes = self.COMMON_SUFFIXES

                        is_common_extension = False
                        for prefix in common_prefixes:
                            if other.startswith(prefix + phrase):
                                is_common_extension = True
                                break
                        for suffix in common_suffixes:
                            if other.endswith(phrase + suffix):
                                is_common_extension = True
                                break

                        if not is_common_extension:
                            to_remove.add(phrase)

        # Remove duplicates that are just common variations
        optimized = [p for p in phrases if p not in to_remove]

        # Sort by length descending to match most specific first
        optimized.sort(key=len, reverse=True)

        return optimized

    def _compile_patterns(self):
        """
        Pre-compile regex patterns to compare against.
        """
        self._optimized_phrases = self._optimize_phrases()

        patterns = []
        for phrase in self._optimized_phrases:
            escaped = re.escape(phrase)  # Escape special regex characters

            # Use word boundaries to match whole words
            # Also handle underscore and dot separators (common in variable names)
            pattern = r"(?<![a-zA-Z0-9_.-])" + escaped + r"(?![a-zA-Z0-9_.-])"
            patterns.append(pattern)

        # Combine all patterns into a single regex with OR
        # Use (?:...) for non-capturing group
        combined_pattern = "|".join(patterns)

        # Compile with appropriate flags
        flags = 0 if self.case_sensitive else re.IGNORECASE
        self._compiled_patterns = re.compile(combined_pattern, flags)

    def is_sensitive(self, text: str) -> bool:
        """
        Check if a string contains sensitive phrases.
        Uses pre-compiled regex for O(1) performance.
        """
        if not text:
            return False

        # Quick length check for performance
        if len(text) < 3:  # Minimum length of any sensitive phrase
            return False

        # Use regex search (stops at first match)
        return bool(self._compiled_patterns.search(text))

    def get_sensitive_phrases(self, text: str) -> list[str]:
        """
        Get all sensitive phrases found in the text.
        """
        if not text:
            return []

        matches = self._compiled_patterns.findall(text)

        # Deduplicate while preserving order
        seen = set()
        unique_matches = []
        for match in matches:
            if match.lower() not in seen:
                seen.add(match.lower())
                unique_matches.append(match)

        return unique_matches

    def mask_sensitive_content(self, text: str, mask: str = "********") -> str:
        """
        Mask sensitive phrases in a string.
        """
        if not text:
            return text

        def replace_match(match):
            return mask

        return self._compiled_patterns.sub(replace_match, text)


def get_sensitive_matcher() -> PatternMatcher:
    """
    Get or create the global sensitive matcher instance.
    """
    global _SENSITIVE_MATCHER

    if _SENSITIVE_MATCHER is None:
        _SENSITIVE_MATCHER = PatternMatcher()

    return _SENSITIVE_MATCHER


def stringify_dict(data: dict[str, typing.Any], flat: bool = False, separator: str = ",") -> str:
    """Convert dict to string.

    Args:
        data (dict): Data to be stringified.
        flat (bool, optional): Flatten out entire data dict
            Default to False
        separator (str, optional): Seperator for items.
            Default to ``,``
    """
    if not flat:
        separator.join(f"{k}:{v}" for k, v in data.items())

    items = []
    for key, val in data.items():
        if isinstance(val, dict):
            items.append(f"{key}:{{{stringify_dict(val, flat, separator)}}}")
        elif isinstance(val, list):
            items.append(f"{key}:[{', '.join(str(v) for v in val)}]")
        else:
            items.append(f"{key}:{val}")

    return separator.join(items)


class ContentMaskingUtils:
    """
    TODO:
        - Improve Email Classification Logic
        - Improve Phone Number Classification Logic
    """

    mask_value: str = "*******"

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Validate if the given email is a valid email
        Validation currently limited to:
        - It has an '@'
        - and there is content before and after '@'

        """
        if (
            "@" in email
            and len(email.split("@")) >= 2
            # and '.' in email
        ):
            return True

        return False

    @staticmethod
    def mask_email(email: str) -> str:
        """Mask out a given email, still giving the intent that its an email"""
        if not ContentMaskingUtils.is_valid_email(email):
            return email

        username, domain = email.split("@")
        if len(username) > 3:
            masked_username = username[:2] + "***" + username[-1]
        else:
            masked_username = "***"

        domain_parts = domain.split(".")
        if len(domain_parts) >= 2:
            masked_domain = domain_parts[0][:2] + "***" + "." + ".".join(domain_parts[1:])
        else:
            masked_domain = "***." + domain_parts[-1]

        return f"{masked_username}@{masked_domain}"

    @staticmethod
    def is_valid_phone(phone: str) -> bool:
        """
        Checks if a valid phonenumber,
        Currently checks if ``10<=digits<=15``
        """
        digits = "".join(filter(str.isdigit, phone))

        if len(digits) >= 10 and len(digits) <= 15:
            return True

        return False

    @staticmethod
    def mask_phone(phone: str, preserve_format: bool = True) -> str:
        """Mask Phone Number, keping the formatting intact for phone number

        Args:
            phone (str): Phone Number string.
            preserve_format (str, optional): Preserve formatting from passed phone number.
                Defaults to True
        """
        if not preserve_format:
            digits = "".join(filter(str.isdigit, phone))
            if len(digits) >= 4:
                masked_digits = "******" + digits[-4:]
            else:
                masked_digits = "****"
            return masked_digits

        formatted = []
        for _, char in enumerate(phone):
            if char.isdigit():
                # TODO: using index Try to keep last four unformatted
                formatted.append("*")
            else:
                formatted.append(char)

        return "".join(formatted)

    @staticmethod
    def filter_value(value: typing.Any, matcher: PatternMatcher) -> typing.Any:
        """Filter a single value if it contains sensitive content."""
        if isinstance(value, str):
            if matcher.is_sensitive(value):
                return ContentMaskingUtils.mask_value

            if ContentMaskingUtils.is_valid_email(value):
                return ContentMaskingUtils.mask_email(value)

            if ContentMaskingUtils.is_valid_phone(value):
                return ContentMaskingUtils.mask_phone(value)

        return value

    @staticmethod
    def filter_sensitive_content(
        stringified: bool = False, deep_search: bool = True, mask_value: str = "********", **attributes
    ) -> typing.Union[dict[str, typing.Any], str]:
        """Filter Sensitive Content from given attributes

        Args:
            stringified (bool, optional): Output required should be stringified or plain dict.
                Default is False
            deep_search (bool, optional): Search Nested Dict's, List's, this take time for large data.
                Default is True, avoid for large amount of attributes.
            mask_value (str, optional): Mask string in place of sensitive content.
                Default value is ``********``

        Kargs:
            attributes unpacked_dict that needs scanning, simply just unpack you'r data dict here

        Usage:

        ```python
        # telematry usage
        ContentMaskingUtils.filter_sensitive_content(stringified=True, **data)

        # api responses
        ContentMaskingUtils.filter_sensitive_content(**data)
        ```
        """
        matcher = get_sensitive_matcher()

        filtered = {}
        mask_value = mask_value or ContentMaskingUtils.mask_value

        for key, val in attributes.items():

            if matcher.is_sensitive(key):
                filtered[key] = mask_value
            else:
                if deep_search:
                    if isinstance(val, dict):
                        filtered[key] = ContentMaskingUtils.filter_sensitive_content(
                            stringified=False, mask_value=mask_value, **val
                        )
                    elif isinstance(val, list):
                        filtered[key] = [
                            (
                                ContentMaskingUtils.filter_sensitive_content(
                                    stringified=False, mask_value=mask_value, **val
                                )
                                if isinstance(item, dict)
                                else ContentMaskingUtils.filter_value(item, matcher)
                            )
                            for item in val
                        ]
                    else:
                        filtered[key] = ContentMaskingUtils.filter_value(val, matcher)

        if stringified:
            return stringify_dict(filtered, flat=True)

        return filtered


def get_object_or_raise(model: type[models.Model], **lookup_kwargs):
    """Get object or raise ObjectNotFound with context"""
    from model_utils.models import SoftDeletableModel

    try:
        if isinstance(model, SoftDeletableModel):
            return model.available_objects.get(**lookup_kwargs)

        return model.objects.get(**lookup_kwargs)
    except model.DoesNotExist:
        raise ObjectNotFound(model=model, **lookup_kwargs)


def safe_get_object_or_raise(model: type["models.Model"], **lookup_kwargs):
    """
    Get object or raise ObjectNotFound with context
    Safe Get the object, if multiple found log the error
    and re-query the db for single instance based on model's ``DEFAULT_ORDERING``
    if no such attribute found fallback to ``-pk``
    """
    from model_utils.models import SoftDeletableModel

    try:
        if isinstance(model, SoftDeletableModel):
            return model.available_objects.get(**lookup_kwargs)

        return model.objects.get(**lookup_kwargs)
    except model.MultipleObjectsReturned as exc:
        LOGGER.error(msg="Multiple Objects found for a unique dataset", exc_info=exc)
        return (
            filter_objects_or_raise(model, **lookup_kwargs).order_by(getattr(model, "DEFAULT_ORDERING", "-pk")).first()
        )
    except model.DoesNotExist:
        raise ObjectNotFound(model=model, **lookup_kwargs)


def filter_objects_or_raise(model: type["models.Model"], **lookup_kwargs) -> "models.QuerySet":
    """Filter for a queryset or raise ObjectNotFound"""
    from model_utils.models import SoftDeletableModel

    qs = None
    if isinstance(model, SoftDeletableModel):
        qs = model.available_objects.filter(**lookup_kwargs)
    else:
        qs = model.objects.get(**lookup_kwargs)

    if not qs:
        raise ObjectNotFound(model, **lookup_kwargs)

    return qs


def camel_to_snake_case(class_name):
    """
    Convert CamelCase string to snake_case.
    Handle consecutive uppercase letters (acronyms) "HTTPResponse" -> "http_response"

    Args:
        class_name (str): String in CamelCase format (e.g., "SomeClassName")

    Returns:
        str: String in snake_case format (e.g., "some_class_name")


    NOTE: Doesn't handle cases when consecutive uppercases occur b/w string
    Example:

        >>> camel_to_snake_case("SomeClassNameNOclasURL")
        >>> 'some_class_name_n_oclas_url'

    """
    pattern = r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])"
    snake = re.sub(pattern, "_", class_name)
    return snake.lower()


class FileHandlingMixin:

    @classmethod
    def correct_file_path(cls, file_path: typing.Union[str, Path]) -> Path:
        """
        Correct file path, relative to base, root, and app directory
        Tries all three, from wherever file is found it returns it

        Args:
            file_path (str): File path

        Returns:
            corrected file path

        Raises:
            SeederException
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        if not isinstance(file_path, Path):
            raise InvalidTypeError(type=type(file_path), expected=type(Path))

        file_path
        if file_path.exists():
            return file_path

        app_path = file_path / settings.APP_DIR
        if app_path.exists():
            return file_path

        base_path = file_path / settings.BASE_DIR
        if base_path.exists():
            return base_path

        raise FileNotFoundError(f"Cannot find: {file_path}")

    @classmethod
    def load_from_file(cls, file_path: typing.Union[str, Path]):
        """
        Load something from a file
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        if not isinstance(file_path, Path):
            raise InvalidTypeError(type=type(file_path), expected=type(Path))

        if not file_path.exists() and not (file_path := cls.correct_file_path(file_path)):
            raise FileNotFoundError(f"File not found: {file_path}")

        data = file_path.read_text()
        if file_path.suffix == "json":
            data = json.loads(data)

        return data
