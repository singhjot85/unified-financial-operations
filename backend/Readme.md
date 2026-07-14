# Backend — Unified Financial Operations Platform

> This is the Backend LLD Index. It documents project-wide Django conventions, the directory layout,
> and serves as the registry of every installed app with a link to its LLD.

---

## Project Layout

```
backend/
├── apps/
│   ├── core/                  # Shared base models, mixins, contracts, app_settings framework
│   │   ├── app_settings/      # BaseSetting descriptor, LazyImport, Constance, registry
│   │   ├── models.py          # BaseModel, BaseLogModel, AbstractParty, DeletionTrackingModel, SimpleVersionModelMixin
│   │   ├── constants.py
│   │   └── serializers.py
│   └── crm/                   # Customer identity, preferences, and relationship domain
│       └── Readme.md          # LLD
├── config/
│   ├── settings/
│   │   ├── base.py            # Main Django settings
│   │   ├── base_models.py     # Centralised app/model string references for swappable FKs
│   │   ├── constances.py      # django-constance config
│   │   ├── setting_variables.py
│   │   └── test.py
│   ├── asgi.py
│   └── wsgi.py
├── manage.py
├── Makefile
├── pyproject.toml
├── lld.template.md            # Template for new app LLD docs
└── Readme.md                  # this file
```

---

## Conventions

### Base Models

All project models inherit from one of the following bases defined in `apps.core.models`:

| Base | Use case | Key fields added |
| :--- | :------- | :--------------- |
| `BaseModel` | Standard domain models | `id` (UUID PK), `created`, `modified`, `is_removed`, `removed_by` |
| `BaseLogModel` | Append-only log / audit tables | `id` (UUID PK), `created`, `modified`, `status`, `status_changed` |

Never inherit from `models.Model` directly for project-domain models.

### Soft Delete

`BaseModel` inherits `DeletionTrackingModel`, which extends `django-model-utils`'s `SoftDeletableModel`.
Calling `.delete()` without `soft=False` marks the row `is_removed=True` and captures `removed_by`.
Hard deletes are allowed but explicit — pass `soft=False`.

### App Settings Framework (`core.app_settings`)

Each app that needs configurable defaults or swappable references declares a `BaseSettings` subclass
in its `app_settings.py`. See `documentation/technical-architecture/app-settings-framework.md` for the
full design. Key descriptor types available:

- `LazyImport` — resolves a dotted-path string to a Python class/object at first access.
- `Constance` — live admin-editable setting backed by `django-constance` (project-wide, not per-tenant).

Override any setting per-project via `settings.<APP>_APP_SETTINGS = { "SETTING_NAME": ... }`.

### Cross-App Foreign Keys — Swappable Reference Pattern

Apps **must not** import another app's model directly (e.g. `from apps.crm.models import Customer`).
Instead, declare a `LazyImport` in the consuming app's `app_settings.py` pointing at the central string
from `config.settings.base_models`. See `documentation/technical-architecture/Readme.md` for the
full pattern and migration (`swappable_dependency`) guidance.

### No Multi-Table Inheritance (MTI)

Platform-wide rule: **single concrete table per entity**. Use a `sub_type` / `customer_type` choice
field on the single table rather than creating subclass models with their own DB tables.
MTI is never used.

---

## App Registry

| App | Label | Schema | Purpose | LLD |
| :-- | :---- | :----- | :------ | :-- |
| `apps.core` | `core` | shared | Base models, mixins, app_settings framework, contracts | _(no separate LLD — conventions documented here)_ |
| `apps.crm` | `crm` | tenant | Customer identity, preferences, and relationship tracking | [crm/Readme.md](./apps/crm/Readme.md) |

> Add a row here whenever a new app is created. Every app row must include the app label (matching
> `AppConfig.name`), which DB schema it lives in (shared public schema vs. tenant schema), a one-line
> purpose, and a link to its `Readme.md`.

---

## Running Locally

```bash
# From project root — via Makefile wrapper
make build        # build Docker images
make run          # start all containers

# Inside the backend container
python manage.py migrate
python manage.py createsuperuser
```

See the root [`Readme.md`](../Readme.md) for full local-setup instructions including seed data.
