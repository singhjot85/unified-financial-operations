# Backend — Unified Financial Operations Platform

> This is the Backend LLD Index. It documents project-wide Django conventions, the directory layout,
> and serves as the registry of every installed app with a link to its LLD.

---

## Project Layout

```
backend/
├── apps/
│   ├── core/                  # Shared base models, mixins, contracts, app_settings framework
│   │   ├── app_settings/      # BaseSetting descriptor, DefferedImport, Constance, registry
│   │   ├── models.py          # BaseModel, BaseLogModel, AbstractParty, DeletionTrackingModel, SimpleVersionModelMixin
│   │   ├── constants.py
│   │   └── serializers.py
│   │   └──  tests/            # Core Tests, independent of app state(s) like models.
│   │
│   └── crm/                   # Customer identity, preferences, and relationship domain
│   |   └── Readme.md          # LLD
│   └── tenants/               # Multi Tenancy models and infra
│   |   └── Readme.md          # LLD
│   └── tests/                 # pytest based tests.
│       └── Readme.md          # Testing Convention(s), related settings and more
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

### Generic Coding Conventions

- Follow these coding conventions when writing and contributing to the project.
- These are not hard and fast rules, but deviating from them should be well explanitory and reasoned.
- Writing a new piece of code must be planned in four phases:
  1. **Analysis Phase:** Identify the input, output and awareness of state of the process/thread that might execute the logic.
  2. **Logical Writing Phase:** Writing simple and clean monolith logic for what needs to be implemented.
  3. **Refactor Phase:** Beaking the monolith code logic into seperate component's.
  4. **Testing Phase:** Validating and testing the written logic.

#### Analysis Phase

**Identifying input:**

- Identify what'll be the input data, ideal data type and possible data type(s).
- Add proper type convention, using `typing` package, for type only import's user `typing.TYPE_CEHCKING`. Ex:

  ```python
  import typing

  typing.TYPE_CEHCKING:
      from django.contrib.auth.models import AbstractUser

  def modify_user(user: "AbstractUser", ...):
      ...
  ```

- How to handle missing data: throw error or get pre-configured data instead of mising inputs.
  - _Throw Error:_ Use a python, django, rest-framework exception, or a custom defined exception.
  - _Use pre-configured data:_ Define in current file, class, corresponding `constants.py` or configure as database object in `apps.setup.models.Configuration` model.
    > _NOTE:_ If relying on `apps.setup.models.Configuration` object, define a fixture at `apps/setup/fixtures/configurations` for an ideal configuration object.

**Identifying Output:**

- Identify if the output is required or not.
- Identify the database object's that the code will be modifying(updating/creating/deleting).
- Identify what'll the piece of code (f/n, class, file) output and in what format.
- Add output type conventions also.

**Identifying State:**

- Identify the current process/thread executing the code, is it the main thread, or an seperaete deligated thread.
  - _Main Thread:_ The thread recieving the user request and returning response.
  - _Deligated Threads:_ These thread/processes are deligated by celery, to execute long-running or I/O bound tasks.
- Identify and plan schema conext and switching that'll take place during execution of the logic.
- Identify and plan database transaction's that'll take place during execution of the logic.

#### Logical Writing Phase

- This is simple but most crucial phase.
- Write the simplest implementation in a big monolith.
- Add checks for mising data, and guards for unexpected behaviour's.
- Define the flow of code in this phase.

We can better understand this using an example, let's take an example of creating a database object creating wrapper from a json data

```python
import typing
from django.db import models

def create_an_object_from_json(model_obj: models.Model, data: typing.Union[dict, tuple, list]):
    # Mising data checks
    if not model_obj:
        raise ObjectCreationException(...)
    if not data:
        raise ObjectCreationException(...)

    # unexpected behaviour checks
    if not isinstance(model_obj, models.Model):
        raise ObjectCreationException(...)
    if not isinstance(data, (list, tuple, dict)):
        raise ObjectCreationException(...)

    for field in model_obj._meta.field():

        # Simplest and trivial frequent case first,
        # save's CPU cycle's and makes debugging easier
        if not field.is_relation
            seattr(model_obj, field.name, data.get(field.name, None))

        # Second Simplest and frequent case then.
        if field.many_to_one or field.one_to_one:
            ...

        # Complex cases at last
        # ... Handle m2m fields ...
        # ... Handle reverse relations ...
```

If you can see we have focused on these technique's while writing above example:

- Handling mising data, and unexpected behaviour's at start of the logic, this prevent un-necessary CPU cycle's and early rasie exceptions.
- The logic start's with handling most trivial and frequent cases first and then the complex cases.
- This method is easy to undestand and break in module's.

#### Refactor Phase:

- Now that we have a clear built out logic, we can break in samller chunks, and reafctor it memory optimizations.
- While refactoring try implementing _DRY (Don't repeat Yourself)_ and _OOP (Obejct Oriented Programming)_ principals.
- Keep a note of the object(s) that the code will create at runtime, and the lifecycle of the object(s) at runtime.
- A fn, class, file serving multiple puposes can cause clutter, split in seperate re-usable/generic helper's/utils.
  Refactoring the above example might look something like:

```python

import typing
from django.db import models

class ObjectCreation:

    def validate_missing_data(self, model_obj, data):
        if not model_obj:
            raise ObjectCreationException(...)
        if not data:
            raise ObjectCreationException(...)

    def valid_unexpected_data(self, model_obj, data):
        if not isinstance(model_obj, models.Model):
            raise ObjectCreationException(...)
        if not isinstance(data, (list, tuple, dict)):
            raise ObjectCreationException(...)

    def validate_data(self, model_obj: models.Model, data: typing.Union[dict, tuple, list]):
        """If you see we have split the data validation in seperate fn's
        General Rule: If a fn contain multiple implementations, split each one in seperate util/helper
            this keeps the code clean and easy to read.
        A Validate fn should only serve one puropose, call different validator's not the actual validation logic.
        """
        self.validate_missing_data(model_obj, data)

        self.valid_unexpected_data(model_obj, data)

        return model_obj, data

    def _set_field_attr(self, model_instance: models.Model, field_name: str, value: typing.Any) -> None:
        """
        Some fields like User.password, file_fields shouldn't be set directly using setattr.
        They need their own seperate logic, this method gives us freedom for that.
        Now we can simply implement a setter seperately for password field:
            >>> def setter_password(self, model_instance: "User", field_name: str, value: typing.Any) -> None:
            >>>     model_instance.set_password(value)
        """
        method_name = f"setter_{field_name}"
        if hasattr(self, method_name):
            return getattr(self, method_name)(model_instance, field_name, value)

        setattr(model_instance, field_name, value)

    def create_object(self, model_obj: models.Model, data: typing.Union[dict, tuple, list]):
        obj, data = self.validate_data(model_obj, data) # A base class can easily override this and change valdiation logic

        for field in model_obj._meta.field():

            if not field.is_relation:
                self._set_field_attr(model_obj, field.name, data.get(field.name, None))

            if field.many_to_one or field.one_to_one:
                self.proces_foreign_relations(...)

            ...

    def create_object(self, model_obj: models.Model, data: typing.Union[dict, tuple, list]):
        try:
            self.create_object(model_obj, data) # Actual Implementation de-coupled from overall lifecycle
        except ObjectCreationException ex:
            raise ex
        except Exception as exe:
            LOGGER.error(exe) # Logging any unwated exeption for later analysis
            raise exe
```

Using the DRY, and OOP practice's we have split a complex monolith logic, into extendable, clean and easy-to-extend solution.

### Testing Phase:

- Whatever logic you build or write, write unittest for individual fn.
- Writing a test for a function make(s) it future proof, that is any change to that method's behaviour won't propogate to deployment.
- Mock/Patch extenal API and I/O calls.
- Write end-to-end flow test for the functionality built, it tests if the feature's works altogether.

### Project Specific Coding Conventions

**Views:**

- A view should only be used to define request and response transaction.
- Always try using DRF viewsets, only in rare cases use Django Views.
- Always send out serialized data.
- Identify and enforce permission(s) required to access that endpoint.
- Do not expose direct error message, implemet custom error's to be exposed.
- Block list endpoints if not required, if exposed always use pagination.
- Clean incoming data, if the data isn't valid throw custom errors, and stop API execution.
- The viewset should not handle the business logic, itself, use a seperate manager/servic.

**URL Patterns:**

- Define all the urls at this base level only, don't break spread out into multiple apps.
- Always use the app_name as `api` for both public and private URLConfig.
- Always try using `router` to register Viewset's, in exterme cases use raw urls.
  - When u already have url's resolved ex: `admin.urls`.
  - When u need to define function based views.
- Use DeafultRouter for deployed envs, we don't want to expose API root view in deplyements.

**Settings:**

- Keep all the backend project settings and configurations in `backend/config/` directory.
- Try keeping it clean, if anything is becoming messy break into files/sub-directories, Ex:
  - Only constant value's in `backend/config/settings/constants.py`, values that may vary at runtime in `backend/config/settings/variables.py`.
  - As settings could have become messy with variable resolution functions created a `backend/config/settings/resolvers.py`.
  - `backend/config/routers.py` only contain Tenant Level routes, `backend/config/public_routers.py` contain Public routes.
  - `backend/config/settings/settings.py` only does definition, everything get defined in helper files/sub-directories.
- Keep all the application related logic in `backend/apps` directory.


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

- `DefferedImport` — resolves a dotted-path string to a Python class/object at first access.
- `Constance` — live admin-editable setting backed by `django-constance` (project-wide, not per-tenant).

Override any setting per-project via `settings.<APP>_APP_SETTINGS = { "SETTING_NAME": ... }`.

### Cross-App Foreign Keys — Swappable Reference Pattern

Apps **must not** import another app's model directly (e.g. `from apps.crm.models import Customer`).
Instead, declare a `DefferedImport` in the consuming app's `app_settings.py` pointing at the central string
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
| `apps.tenants` | `tenants` | public | Tenant, Domain, and TenantSetup Related framework | [tenants/Readme.md](./apps/tenants/Readme.md) |

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
