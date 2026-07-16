# Backend Testing Suite

## Purpose

Automated test suite for validating business logic and multi-tenant integrity.

The BMA testing suite prioritizes fast, isolated, and reliable tests using `pytest`. It ensures that tenant data remains isolated and that core features like invoicing and payments function correctly across different schemas.

## Quick Start

```bash
# Run the full suite
pytest

# Run tests for a specific app
pytest backend/tests/customer_management/

# Run for a specific filter
pytest -k <test-filter>
```

Avoid using direct pytest command's use make target's to run tests

```bash
# Run entire test suite
make t

# Run entire test in entire diectories
make tf TEST_DIR=

# Run tests based on a name filter
make tf TEST_FILTER=
```

## Key Concepts

- **Multi-Tenant Isolation**: Tests run in dedicated schemas to verify `django-tenants` boundaries.
- **Eager Tasks**: `CELERY_TASK_ALWAYS_EAGER = True` ensures background tasks run synchronously during tests.
- **Factory-Boy**: Centralized factories (`factories.py`) manage complex test data generation.
- **Given-When-Then**: Standardized test structure for clarity and maintainability.

## Testing Conventions

tests written using `pytest` follow _Arrange-Act-Assert_ methodology, that is what we are going to follow in our project tests. Prefer writing test classes rather then scattered classes.

- **Arrange:**
  - Naming: `test_subject__condition__result` or `test_method_name__scenario__expected_behavior`.
  - `setup_method` to setup common data for class.
  - `_<get_some_data>` private functions for dynamic and common data setup among tests under a class.
  - factories to create models, they handle their own cleanup.
  - `unittest.mock.patch`, `unittest.mock`, `unittest.MagicMock` instead of complex object building, external APIs and heavy services.
- **Act:**
  - Identify what the test is aimed for and only call that callable (`function`, `class`, `property`).
  - Before calling the callable, go through the code and identify setup and asserts.
  - Re-verify if everything is setup properly, and pass what the callable achieve(s) to assert phase.
- **Assert:**
  - `refresh_from_db(using="default")` before asserts.
  - Aim minimal logical assertion(s) per test to maintain focus.
  - Tests must clean up after themselves.

## Configuration

- **Pytest**:
  - Configured via `pyproject.toml` with strict marker checks and short tracebacks.
  - Configured python files: `test_*` or `*_test`, classes: `Test*`, `*Tests`, functions: `test_*`.
  - Configured testpath `tests`.
  - Arguments for pytest command:
    - `-v`: Log verbosity.
    - `--reuse-db`: reuses database and make tests fast.
    - `--import-mode=importlib`: To prevent issue's when two files have same name.
  - Current Declared Markeres: `slow`, `integration`, `unit`, `celery`.
- **Settings**:
  - Uses `config.settings.test` which overrides hashers (MD5 for speed) and caches (LocMem).
  - Default database fot tests is `pytest_db`(see DATABASE.NAME in [settings](../config/settings/test.py)).
  - By default tests run in tenant schema `test_schema` (see TENANT_SCHEMA_NAME in [settings](../config/settings/test.py)).
  - To switch to public schema for a specific tests you can use `public_db` fixture or `django_tenants.utils.schema_context`.
  - `CELERY_TASK_ALWAYS_EAGER` to run tasks synchronously `CELERY_TASK_EAGER_PROPAGATES` to show celery exceptions.
  - Django's `LocMemCache` used to make tests fast.
  - Django's console Email Backend used to prevent I/O operations and make tests faster.

## Core Tests

- Test Specific Core Moudule remains at core only: [CORE Tests](../apps/core/tests/__init__.py).
- These tests are indepent of app state(s), they should only test core and realed state(s).
- These may include unit tests or complete workflow tests.
- These tests should not depend on ant app, module out of core.
- Model Classes, Admin Classes, etc. required to run these tests should either be mocked or written purely for testing purpose.
- If any Model Classes, Admin Classes, etc. is written for tests there should be a proper teardown.

## Testing

- Automated via CI/CD pipelines.
- Manual execution recommended before every commit using `pytest`.
