---
name: backend-test-writer
description: "Write unit and integration tests for the BMA backend following project conventions. Use when explicitly requested to add tests, or when implementing new features that require test coverage (views, models, forms, serializers, multi-tenant logic)."
---

## When to Use

Invoke this skill when:

1. **Explicit request**: User asks to "write tests for X", "add test coverage", "create unit tests"
2. **New feature implementation**: Adding a new model, view, serializer, form, or business logic
3. **Bug fix**: Writing regression tests for defects
4. **Refactoring**: Backfilling tests for existing code being modified

## Testing Conventions to Enforce

The test suite mirrors the structure of the `apps/` directory to ensure discoverability:

```text
backend/
	|- apps/
		|- tests/ 				# Core module related tests
	|- tests/
		|- conftest.py          # Project-wide fixtures and pytest configuration
		|- factories.py         # Centralized factory-boy definitions
		|- crm/ # App-specific tests
		│   |- __init__.py      # Required for proper module resolution
		│   |- conftest.py      # App-level fixtures (e.g., specific tenant setups)
		│   |- test_models.py
		│   |- test_views.py
		|- tenants/             # Multi-tenant isolation and provisioning tests
```

- Prefer Class Based Tests, over function based tests.
- For Detailed Testing Convention refer: [Backend Testing Convention](../../../backend/tests//Readme.md)
- For Any confusion refer: [Backend Documentation](../../../backend/Readme.md)

## Step-by-Step Test Generation

### Step 1: Analyze the Code

- Identify the app (e.g., `customer_management`, `tasks`).
- If the app directory doesn't exist in `tests/`, create it and add `__init__.py`.
- Determine test type: model, view, serializer, form, task.
- Identify dependencies (other models, tenant requirements).
- Identify what will be available at runtime taking reference from [Test Documentation](../../../backend/tests/Readme.md), if something is not available at runtime, mock it.

### Step 2: Plan Test Cases

- Happy path (normal operation).
- Edge cases (nulls, empty strings, boundary values).
- Error cases (validation, permissions, not found).
- Multi-tenant isolation (cross-tenant data leakage).
- Celery tasks: Note that `CELERY_TASK_ALWAYS_EAGER = True` is used, so tasks run synchronously.

### Step 3: Generate Tests

- Create appropriate file in `backend/tests/<app_name>/test_*.py`.
- Break large functionality into atomic functional components.
- Group tests for related features in test classes.
- Mock the data using factories and mock data in `setup_method()`.
- Patch complex logic(s) to maintain atomicity in tests.
- Feed the expected data (variables, objects, etc.) to the callable.
- Assert that the outcome of the callable matches the expected outcome.
- Test error paths and edge cases wherever applicable.

### Step 4: Imports, DocString, TypeConvetion

- Insure all necessary imports are there.
- After writing the tests, verify the import's, add mission imports and remove unwanted imports.
- Add clear and concise docstring.
- Add necessary type conventions.
- imports required only for type convention should be always under typing.TYPE_CHECKING.

### Step 5: Run Validation

- After writing tests, suggest running.
- Always run tests in docker setup.
```bash
docker compose -f compose/compose.local.yaml run django pytest tests/<app_name>/test_*.py
```
- Use following make targets to make testing easier:
```bash
# Run all tests
make t

# Run all tests in a specific directory
make tf TEST_DIR=<directory_path>

# Run filtered tests
make tf TEST_FILTER=<test_filter>

# Run filtered tests fast (makes test discovery fast)
make tf TEST_DIR=<directory_path> TEST_FILTER=<test_filter>
```

## Anti-Patterns to Avoid

- Hardcoding schema names; use `tenant_context` or, better, use tenant fixtures.
- **Don't** use Django `TestCase` unless necessary; always prefer plain pytest tests.
- **Don't** write tests for trivial conditions; always test functionality. Example: `2+2=4` doesn't require a test; it's trivial.
- Write tests to prevent accidental functionality deviation and ensure consistency of code behavior.

## Output Format

When generating tests, provide:

1. **Brief explanation** of what tests are being added
2. **The test code** with proper imports and docstrings
3. **Instructions** to run the tests
4. **Any new factories** needed (if applicable)
