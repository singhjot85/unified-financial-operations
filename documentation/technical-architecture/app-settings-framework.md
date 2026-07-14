# HLD: Core App Settings Framework

> Location: `documentation/technical-architecture/app-settings-framework.md` <br/>
> Status: `Approved` <br/>
> Owner: <name> <br/>
> Last updated: 2026-07-15 <br/>
> Related BRD: N/A — internal developer-experience / architecture infrastructure, not a user-facing feature <br/>
> Related ADRs: None currently — see "Alternatives considered" below for the point-decisions folded into this doc <br/>
> Implementing app(s): `core.app_settings` (new); consumed by every app defining an `app_settings.py` (`crm`, `ledger`, `notification_app`, `donation_management`, `expense_management`, and future apps) <br/>

---

> **Implementation status:** `core.app_settings` is partially implemented. `base.py` has `BaseDescriptor` (full implementation) and `BaseSettings` (stub — no metaclass or registry walk yet). `types.py` has `LazyImport` and `Constance` stubs (classes with `pass`). `registry.py` is empty. `LazyModelImport` is designed in this doc but not yet implemented. `crm/app_settings.py` uses `LazyImport` and `Constance` directly (working via the descriptor mechanism in `base.py`). The full framework described here is the target design; the current code partially implements it.

## What

A descriptor-based framework, rooted in `core.app_settings`, that gives every app in the platform a single, consistent convention for declaring configurable settings — whether those settings are lazily-imported Python objects, lazily-resolved Django model classes, admin-editable runtime toggles (via `django-constance`), or plain non-persisted runtime flags. Each app declares one `BaseSettings` subclass (e.g. `CRMSettings`) in its `app_settings.py`, instantiated once as `app_settings`, whose fields are accessed as plain attributes (`app_settings.PARTY_TYPE_CHOICES`) and resolve transparently to their runtime value — import, model class, live DB value, or plain override — without the caller needing to know which mechanism backs a given setting.

This generalizes two patterns already established in the platform: Django's own swappable-model convention (`AUTH_USER_MODEL`-style FK targets, already used for `CRM_CUSTOMER` and friends), and the existing `project_settings.<APP>_APP_SETTINGS` override dict. It does **not** replace the existing swappable-FK string-setting convention used for `ForeignKey`/`swappable_dependency()` targets — that stays a plain string, deliberately outside this framework's descriptor mechanism, for reasons covered under Key models / contracts.

## Why

- Every app currently needs some mix of: importable defaults that a project may want to override (choice classes, strategy classes), model references consumed differently depending on context (migrations vs runtime code), and runtime toggles (some needing live admin editability via constance, some not). Without a shared convention, each app would invent its own ad hoc pattern for these, inconsistent with the loosely-coupled-apps architecture already in place (`app_settings.py` + `project_settings.<APP>_APP_SETTINGS` override, `checks.py` validation) documented in the platform summary.
- Constance-backed settings in particular have a lifecycle hazard (DB-table registration must happen before migrations/admin touch the constance app) that, if left to each app to handle independently, risks import-order bugs that are hard to trace back to their cause.
- Without this framework, `LazyImport`-style resolution (dotted-path imports, lazy model resolution) would likely get reinvented per-app with subtly different — and in some cases lifecycle-unsafe — implementations (e.g. eagerly calling `apps.get_model()` at module import time, causing intermittent `AppRegistryNotReady` depending on import order).

## How

### Components involved

- **`core.app_settings`** (new): houses the `BaseSetting` descriptor base class, the four concrete setting types, the `BaseSettings` container/metaclass, and the Constance registration registry.
- **Per-app `app_settings.py`** (existing convention, now formalized): each app declares a `BaseSettings` subclass and instantiates it once as `app_settings`.
- **Per-app `apps.py` (`AppConfig.ready()`)**: explicitly triggers Constance-field registration and (optionally) fail-fast validation of `LazyImport`/`LazyModelImport` targets, for that app's `app_settings` instance.
- **`project_settings.<APP>_APP_SETTINGS`**: existing override dict convention, unchanged in shape, now the single override surface consumed by all four setting types (with Constance treating it as a _seed default_ rather than a live override — see below).
- **`django-constance`**: existing dependency, now driven by this framework's registry rather than manually-maintained `CONSTANCE_CONFIG` entries per app.

### Data flow

**Declaration → registration (startup):**

```
models.py imports app_settings.py
  → app_settings.py executes CRMSettings() at module scope
    → BaseSettings.__init__ collects declared BaseSetting fields (introspection only — no side effects)
  → (later, during django.setup()) CrmConfig.ready() fires
    → explicitly calls register_constance_fields(app_settings)
      → walks declared Constance fields, writes settings.CONSTANCE_CONFIG[...] and
        CONSTANCE_CONFIG_FIELDSETS[<APP_LABEL>] entries
    → (optional) explicitly calls settings-validation check
      → walks declared LazyImport / LazyModelImport fields, confirms each resolves,
        fails fast with an app-namespaced Error if not
```

**Access (runtime, per-request or per-task):**

```
app_settings.PARTY_TYPE_CHOICES
  → LazyImport.__get__ → override lookup in project_settings.CRM_APP_SETTINGS → importlib resolve (cached by path) → return class

app_settings.CRM_CUSTOMER_MODEL
  → LazyModelImport.__get__ → override lookup → apps.get_model(app_label, model_name) → return model class
  (only safe post-ready(); by construction this is always the case in views/signals/serializers/tasks)

app_settings.raw("CRM_CUSTOMER_MODEL")
  → LazyModelImport.raw_string(instance) → override lookup only, no apps.get_model() call → returns "crm.Customer" string
  (used inside migration files, e.g. migrations.swappable_dependency(...), where apps.get_model() is unsafe/undefined)

app_settings.ENABLE_SOME_CUSTOMER_RELATED_FLAG
  → Constance.__get__ → constance.config.CRM__ENABLE_SOME_CUSTOMER_RELATED_FLAG (live DB read; project_settings has no say post-registration)

app_settings.STRICT_EMAIL_REQUIRED
  → Flag.__get__ → live read of settings.CRM_APP_SETTINGS (no caching, so override_settings works transparently in tests)
```

### Key models / contracts

**`BaseSetting`** (abstract, template pattern): defines `__set_name__` (captures field name), `get_raw_value()` (override lookup against `project_settings.<APP>_APP_SETTINGS`, falling back to `default`), and an abstract `resolve()` that subclasses implement. `__get__` orchestrates: fetch raw value → `resolve()` → optional `type_cast`. Class-level access (`SomeSettings.FIELD`, not `instance.FIELD`) returns the descriptor itself, not a resolved value — needed for introspection (the registry walks descriptors, not resolved values).

**`LazyImport[T]`** (`Generic[T]`, explicit type param at every declaration site): dotted-path string → `importlib` resolve, cached by path string (process-global cache; safe because import targets don't change without a redeploy). `__set__` writes directly into the resolution cache — a test-only escape hatch, not a `project_settings` mutation.

**`LazyModelImport[T]`** (`Generic[T]`): `"app_label.ModelName"` string → `apps.get_model(...)`, resolved lazily on first attribute access, never at class-body-eval or `app_settings.py` module-execution time. Exposes a parallel `raw_string(instance)` path (surfaced via `BaseSettings.raw(name)`) that returns the plain override string **without** calling `apps.get_model()` — this is the path migrations use. Deliberately **not** merged into a single string-subclass-with-a-`.model`-property design: a dual-purpose object that's simultaneously string-like and lazily-model-like was rejected because it would make an unsafe access pattern (`apps.get_model()` inside a migration `RunPython`) look syntactically indistinguishable from a safe one. `.raw(name)` vs plain attribute access are the two explicit, non-ambiguous entry points instead.

**`Flag`**: plain runtime value, override-dict lookup only, no caching, no DB, no admin surface. `__set__` raises `AttributeError` by design — `django.test.override_settings` is the sanctioned way to vary it in tests; a real runtime `__set__` would silently reintroduce the exact hazard `override_settings` exists to contain.

**`Constance`**: two-phase — **registration** (`AppConfig.ready()` → `register_constance_fields()`, builds `CONSTANCE_CONFIG` + `CONSTANCE_CONFIG_FIELDSETS` entries, keyed `<APP_LABEL_UPPER>__<FIELD_NAME>` to avoid cross-app key collisions) and **access** (`__get__`/`__set__` read/write `constance.config.<NAMESPACED_KEY>` directly, live from the DB). `default` only seeds the initial `CONSTANCE_CONFIG` tuple (which `project_settings` _can_ influence, pre-migration); once a DB row exists, `project_settings` has no further effect — that live-editability is the entire reason to reach for `Constance` over `Flag`.

**Swappable-FK string setting** (existing convention, explicitly _not_ absorbed into this framework): `CRM_CUSTOMER = 'crm.Customer'`-style settings stay plain strings, consumed by `swappable_dependency()` and `ForeignKey('crm.Customer')`. Kept outside the descriptor mechanism because `swappable_dependency()` executes at migration-file _import_ time — before any guarantee that the app registry is in a state where `apps.get_model()` is safe. `LazyModelImport` and the swappable-FK string may reference the same underlying dotted target conceptually, but are declared as two distinct settings (e.g. `CRM_CUSTOMER` as the plain string, `CRM_CUSTOMER_MODEL` as the `LazyModelImport`), so a `project_settings` override only has to change one value to redirect both call sites consistently.

### Integration points

- `django-constance` (`CONSTANCE_CONFIG`, `CONSTANCE_CONFIG_FIELDSETS`) — driven by this framework's registry instead of manual per-app entries.
- Existing `project_settings.<APP>_APP_SETTINGS` override convention — unchanged shape, now the single override surface for all four types.
- Existing `checks.py` / `missing_attrs` pattern — the optional fail-fast validation of `LazyImport`/`LazyModelImport` targets in `AppConfig.ready()` is a natural companion to this pattern, using the same app-namespaced `Error`/`Warning` id convention (e.g. `crm.E00X`).
- Django app registry / `AppConfig.ready()` lifecycle — Constance registration and settings validation are explicitly triggered here rather than as a side effect of `BaseSettings.__init__`, to avoid import-order-dependent behavior.

### Alternatives considered

- **Unifying `LazyModelImport` with the swappable-FK string setting** into one dual-purpose descriptor (string usable directly by `swappable_dependency()`, with a `.model` property for runtime resolution). Rejected: migrations need a plain string with zero app-registry dependency at import time; a descriptor that's simultaneously string-like and lazily-model-resolving makes an unsafe call pattern inside a migration indistinguishable, syntactically, from a safe one. Kept as two explicit declarations instead.
- **Registering `Constance` fields inside `BaseSettings.__init__`** (i.e. as a side effect of `app_settings = CRMSettings()` executing, itself a side effect of whatever `models.py` happens to import it first). Rejected: works today only incidentally, because Django currently imports all `models.py` files before running any `AppConfig.ready()` — not something this design should rely on. Moved registration to an explicit call inside each app's `AppConfig.ready()`.
- **Real static typing for `LazyImport`/`LazyModelImport` via bare `type_cast`** with no `Generic` parameter. Rejected: a checker can't infer a resolved import's type from a runtime coercion callable; `Generic[T]` with an explicit type parameter at every declaration site is more ceremony but is the only version that actually gives IDE/mypy the resolved type.
- **Uniform `__set__` support across all four types.** Rejected: `Constance`'s write-through to the DB is the entire point of using it; `Flag` has no storage layer to write through to, so a real `__set__` would just reintroduce the hazard `override_settings` exists to manage in tests — made to raise `AttributeError` instead.

## Directory Structure

```
core/app_settings/
├── base.py         # BaseDescriptor (full implementation), BaseSettings (stub — no metaclass yet)
├── types.py        # LazyImport (stub), Constance (stub); LazyModelImport not yet implemented
├── registry.py     # register_constance_fields() — empty, not yet implemented
└── __init__.py

apps/<app_name>/
├── app_settings.py   # per-app BaseSettings subclass + `app_settings = <App>Settings()` instance
├── apps.py           # AppConfig.ready() — Constance registration call not yet wired up
├── models.py         # imports app_settings.py directly at module top
├── migrations/        # uses app_settings.raw(<name>) for swappable_dependency() [once LazyModelImport is built]
└── checks.py          # existing missing_attrs-based checks
```

## Miscellaneous

- **Open questions / known unknowns:**
  - Whether the fail-fast `AppConfig.ready()` validation of `LazyImport`/`LazyModelImport` targets ships in this first iteration or is deferred — mechanism is cheap to add given the registry already walks every declared field, but not yet built.
  - Naming convention for the paired swappable-FK-string / `LazyModelImport` declarations (e.g. `CRM_CUSTOMER` + `CRM_CUSTOMER_MODEL`) is a DX call, not a lifecycle constraint — worth confirming per-app as apps are built rather than mandating a single suffix convention up front.
- **Rollout plan:** no feature flag needed — this is internal developer infrastructure, not a runtime-gated feature. Rollout is simply: build `core.app_settings`, migrate `crm`'s existing `app_settings.py` (if any informal version exists) onto it first as the reference implementation, then require it for every new app going forward.
- **Non-functional considerations:**
  - Multi-tenancy: `Constance` values are project-wide (public-schema), not per-tenant — any setting needing per-tenant runtime editability should continue to use the tenant `Configurations` JSON field described in the platform summary, not `Constance`. Worth flagging explicitly in app-level LLDs wherever a `Constance` field is declared, so it isn't mistaken for tenant-scoped.
  - `LazyImport`'s cache is process-global, keyed by path string — fine for production; under test, don't `importlib.reload()` a module whose resolved object is cached, patch the target object instead.
- **Changelog:**
  - 2026-07-15 — Added implementation status note: `BaseDescriptor` in `base.py` is fully implemented; `BaseSettings` is a stub; `types.py` has stub `LazyImport`/`Constance`; `LazyModelImport` and `Flag` are designed but not yet coded; `registry.py` is empty. Updated directory structure accordingly.
  - 2026-07-12 — Initial version, consolidating the full design discussion (setting-type contracts, lifecycle analysis, `LazyModelImport`/swappable-FK separation, Constance registration timing).
