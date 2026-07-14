# LLD: `crm`

> Location: `backend/apps/crm/README.md` <br/>
> Status: `Active` <br/>
> Owner: <name> <br/>
> Last updated: 2026-07-15 <br/>
> Implements HLD: [`documentation/technical-architecture/crm.md`](../../../documentation/technical-architecture/crm.md) <br/>
> Related ADRs: None <br/>

---

## What

`crm` owns the platform's canonical identity model, `crm.Customer`, along with its related sub-models: `CustomerEmail`, `CustomerPhone`, `CustomerEntity`, `CustomerPreferenceType`, and `CustomerPreference`. It is the **source** of the swappable identity reference every other app consumes — it does not itself define a `CRM_CUSTOMER`-style swappable setting, because it has no need to swap out its own canonical model.

> **Implementation status:** The `Customer` identity layer and preference system are implemented. The sales/relationship layer described in the HLD (`Lead`, `Pipeline`, `Stage`, `Deal`, `DealStageHistory`) is **not yet built** — those models are HLD-planned but absent from the current codebase. This doc covers only what currently exists.

## Why

Every other module (Donations, Invoicing, Notifications, Expenses) needs a canonical notion of "who." Rather than let each app invent its own version of "a contact," this app owns that identity once, and every other app references it through the swappable-FK convention. This keeps `crm` reusable as a standalone identity layer across projects.

## Python / Django Concepts

### `on_delete` behavior, specifically `PROTECT`

**What it is:** Every `ForeignKey` needs an `on_delete` argument telling Django what to do to rows that reference a target row when that target gets deleted. `PROTECT` raises `ProtectedError` and refuses the delete outright if any referencing rows exist.

**Why this app needs it:** `CustomerEmail` and `CustomerPhone` use `PROTECT` on their `customer` FK — once contact records exist for a Customer, that Customer cannot be hard-deleted while those records remain. This is expected; use the soft-delete path instead (see BaseModel).

**Minor example:** `models.ForeignKey(Customer, on_delete=models.PROTECT)` — attempting `customer.delete(soft=False)` while any `CustomerEmail` still points at it raises `ProtectedError`.

### Concrete (single-table) inheritance vs. Multi-Table Inheritance (MTI)

**What it is:** MTI creates a separate DB table per child model, joined via a `OneToOneField`. The platform-wide alternative is a single concrete table per entity, with variation captured via choice fields.

**Why this app needs it:** `Customer` represents both individual people and business entities (`party_type`), and different business contexts (NGO donor, SMB client, backoffice — `customer_type`), without separate tables. A single table keeps cross-type queries trivial.

### Descriptor-based `app_settings` framework (`core.app_settings`)

**What it is:** Each app declares a `BaseSettings` subclass in `app_settings.py`. Field values are resolved at access time via descriptors (`LazyImport`, `Constance`), not at import time.

**Why this app needs it:** `crm` uses `LazyImport` for swappable choice classes (`PartyTypeChoices`, `CustomerTypeChoices`, `PreferenceDataTypeChoices`), the swappable preference-validator class (`PREFERNCE_TYPE_VALIDATOR`), and the auth user model (`AUTH_USER`). This lets any of these be overridden per-project via `settings.CRM_APP_SETTINGS`.

**Minor example:**
```python
# crm/app_settings.py
PARTY_TYPE_CHOICES = LazyImport(default="apps.crm.constants.PartyTypeChoices")
```
```python
# project settings override
CRM_APP_SETTINGS = {"PARTY_TYPE_CHOICES": "myproject.constants.CustomPartyTypeChoices"}
```

### Abstract validator mixin (`AbstractPreferenceTypeValidator`)

**What it is:** An abstract base class (`abc.ABC`) in `abstacts.py` that defines the interface a preference-type validator must implement: `validate_metadata`, `set_metadata`, `get_metadata`.

**Why this app needs it:** `CustomerPreferenceType` inherits from both `BaseModel` and a validator class resolved at runtime via `app_settings.PREFERNCE_TYPE_VALIDATOR`. Decoupling the interface (abstract class) from the default implementation (`PreferenceTypeValidator`) allows projects to swap in custom validation logic without modifying model code. The resolved class is captured once at module load into `PreferenceTypeValidatorOverride`.

## LLD Concepts

### Being the _source_, not a _consumer_, of a swappable reference

**The pattern:** The plain string target `CRM_CUSTOMER = "crm.Customer"` lives centrally in `config.settings.base_models`. Each _consuming_ app that needs the resolved class form declares its own `LazyImport` in its `app_settings.py`, pointing at that central string. `crm` itself declares neither — it doesn't need a swappable reference to its own model.

**Why this app follows it:** Swappable references exist to let a consuming app be redirected at a different target model. `crm.Customer` is simply `crm.Customer` from its own perspective; there's nothing to swap from inside `crm`.

### Swappable choices and validator via `CRM_APP_SETTINGS`

**The pattern:** Rather than hardcoding `PartyTypeChoices`, `CustomerTypeChoices`, etc. directly in model field definitions, they are declared as `LazyImport` settings in `CRMSettings` and accessed via `app_settings.<SETTING>`. This lets a project substitute a different choices class without touching model code.

**Why this app follows it:** The platform serves multiple client types (NGO, SMB, Individual). Different deployments may need different valid values for `party_type` or `customer_type` without forking the app.

### The preference type validator pattern

**The pattern:** `PreferenceTypeValidator` is a concrete Python class (not a model) that handles validation and transformation of the `additional_meta_data` JSON field on `CustomerPreferenceType`. It is declared as a `LazyImport` setting so projects can provide a custom validator. `CustomerPreferenceType` inherits from both `BaseModel` and the resolved validator class at module load time via `PreferenceTypeValidatorOverride`.

**Why this app follows it:** The `additional_meta_data` JSON has a context-dependent structure (different fields for `CHOICES` vs `BOOLEAN` data types). Encapsulating that logic in a swappable class keeps the model clean and makes the validation behaviour replaceable.

## Anti-patterns

**A consuming app importing `from apps.crm.models import Customer` directly.**
_What it looks like:_ Any direct model import from another app's `models.py`, `signals.py`, or elsewhere.
_Why it's wrong:_ Hardcodes the dependency, defeating the swappable-FK pattern — the consuming app can no longer be redirected at a different customer model without editing source code.
_Do instead:_ Declare a `LazyImport` in the consuming app's `app_settings.py`, pointing at the central string in `config.settings.base_models`.

**Using Multi-Table Inheritance to model party types or customer types as subclasses.**
_What it looks like:_ `class IndividualCustomer(Customer): ...` or `class DonorCustomer(Customer): ...`.
_Why it's wrong:_ Platform-wide golden rule violation — every cross-type query needs a join, migrations touching shared fields must consider multiple tables.
_Do instead:_ Use the `party_type` / `customer_type` choice fields already on `Customer`.

**Assuming `crm` needs a `CRM_CUSTOMER` setting just because every consumer has one.**
_What it looks like:_ Adding `CRM_CUSTOMER = LazyImport(...)` inside `CRMSettings`.
_Why it's wrong:_ `crm` is the source, not a consumer. It defines the canonical model; there is nothing to swap from its own perspective.
_Do instead:_ Leave `CRM_CUSTOMER` as a plain string in `config.settings.base_models`, and let only consuming apps declare `LazyImport` fields pointing at it.

**Calling `apps.get_model()` at module import time (e.g. at the top of `models.py`).**
_What it looks like:_ `Customer = apps.get_model("crm", "Customer")` outside any function/method.
_Why it's wrong:_ `AppRegistryNotReady` — the app registry is not populated until after all `models.py` files have been imported. `LazyImport` / `LazyModelImport` descriptors exist precisely to defer this until first attribute access, post-`django.setup()`.
_Do instead:_ Use `LazyImport` or `LazyModelImport` in `app_settings.py`; access the resolved class via the descriptor, never at module scope.

## How

- **Models:**
  - `Customer` — canonical identity model. Inherits `BaseModel` + `AbstractParty` (suffix, first_name, middle_name, last_name, business_name). Key fields: `party_type` (Individual / Entity), `customer_type` (Donor / BackOffice / Client), `customer` (self-referential FK for hierarchical grouping, nullable), `dob`, `user` (FK to `AUTH_USER`, nullable, `PROTECT`).
  - `CustomerEmail` — one-to-many emails per Customer. Fields: `is_primary`, `email`, `type` (Primary/Secondary/Tertiary). FK to `Customer` with `PROTECT`.
  - `CustomerPhone` — one-to-many phone numbers per Customer. Fields: `is_primary`, `phone`, `type` (Primary/Secondary/Tertiary). FK to `Customer` with `PROTECT`.
  - `CustomerEntity` — links a Customer to an arbitrary other model instance via a `GenericForeignKey` (`entity_content_type` + `entity_object_id`). FK to `Customer` with `PROTECT`.
  - `PreferenceTypeValidator` — concrete implementation of `AbstractPreferenceTypeValidator`. Not a model; lives in `models.py` as the default class resolved by `app_settings.PREFERNCE_TYPE_VALIDATOR`. Handles metadata validation for `CustomerPreferenceType`.
  - `CustomerPreferenceType` — defines a named preference key (`preference_name`), its `data_type` (integer / boolean / string / choices), and an `additional_meta_data` JSON field holding label, default, multi-select flag, and optional choices list. Inherits from `BaseModel` and the resolved validator class.
  - `CustomerPreference` — the per-customer value for a given `CustomerPreferenceType`. FK to both `CustomerPreferenceType` and `Customer` (both `PROTECT`). Value stored in a `JSONField`.

- **Swappable settings (`CRM_APP_SETTINGS`):**

  | Setting | Default | Purpose |
  | :------ | :------ | :------ |
  | `PARTY_TYPE_CHOICES` | `apps.crm.constants.PartyTypeChoices` | Choices for `Customer.party_type` |
  | `CUSTOMER_TYPE_CHOICES` | `apps.crm.constants.CustomerTypeChoices` | Choices for `Customer.customer_type` |
  | `PREFERENCE_DATA_TYPE_CHOICES` | `apps.crm.constants.PreferenceDataTypeChoices` | Choices for `CustomerPreferenceType.data_type` |
  | `PREFERNCE_TYPE_VALIDATOR` | `apps.crm.models.PreferenceTypeValidator` | Validator class mixed into `CustomerPreferenceType` |
  | `AUTH_USER` | `django.contrib.auth.models.User` | Target for `Customer.user` FK |
  | `ENABLE_SOME_CUSTOMER_RELATED_FLAG` | `True` | Example Constance-backed flag (admin-editable) |

- **Contracts / checks:** `crm` currently has no `checks.py`. It is the identity source; consuming apps validate the shape of `crm.Customer` against their own `REQUIRED_CRM_CUSTOMER_ATTRS` lists in their own `checks.py` files.

- **Migrations:** Standard — no data migration from any prior model. `crm` is a fresh-start identity layer.

- **Signals / side effects:** None currently implemented.

- **API surface:** `serializers.py` and `views.py` exist but are not yet finalized — to be filled in once the DRF layer for CRM is built.

- **Gotchas:**
  - `PREFERNCE_TYPE_VALIDATOR` has a typo in the setting name (missing 'E': `PREFERNCE` not `PREFERENCE`). This is the live spelling used in `app_settings.py` and `models.py` — do not rename it without a coordinated find-replace, as it would be a breaking change for any project overriding this setting.
  - `CustomerPreferenceType` inherits from the *resolved* validator class captured at module load time as `PreferenceTypeValidatorOverride = app_settings.PREFERNCE_TYPE_VALIDATOR`. This means the MRO (method resolution order) is set once when `models.py` is first imported — a runtime `CRM_APP_SETTINGS` override applied after that point has no effect on already-imported models.
  - `Customer.customer` is a self-referential FK (`ForeignKey("self", on_delete=SET_NULL)`) — used for grouping related customers (e.g. an individual under a corporate entity). Avoid deep recursive trees; there is no cycle-detection guard.

## Directory Structure

```
backend/apps/crm/
├── __init__.py
├── abstacts.py          # AbstractPreferenceTypeValidator — interface for the swappable validator
├── admin.py
├── app_settings.py      # CRMSettings (BaseSettings subclass) + app_settings instance
├── apps.py              # CrmConfig (AppConfig)
├── constants.py         # CustomerTypeChoices, PartyTypeChoices, EmailTypeChoices, PhoneTypeChoices, PreferenceDataTypeChoices
├── migrations/
│   └── __init__.py
├── models.py            # Customer, CustomerEmail, CustomerPhone, CustomerEntity, PreferenceTypeValidator, CustomerPreferenceType, CustomerPreference
├── serializers.py       # not yet finalized
├── views.py             # not yet finalized
└── Readme.md            # this file
```

## Miscellaneous

- **HLD-planned, not yet implemented:** `Lead`, `Pipeline`, `Stage`, `Deal`, `DealStageHistory`, and `CustomerAddress` models described in the HLD (`documentation/technical-architecture/crm.md`) do not yet exist in this app. When built, update this LLD with their model descriptions, FK notes, and the `PROTECT` / soft-delete consideration for `Lead.converted_customer`.

- **Open questions:**
  - **Won-Deal → Donation/Invoice hand-off mechanism** — signal-driven vs. explicitly orchestrated; not yet relevant since Deal is not built.
  - **`REQUIRED_CRM_CUSTOMER_ATTRS` baseline** — consuming apps will need to declare which fields they depend on once they are built (`id`, `display_name`, `email`, `phone` per the HLD baseline — but `Customer` currently doesn't have a `display_name` field; it has `AbstractParty` name parts instead). This needs to be resolved when the first consuming app is wired up.
  - **Soft-delete vs. `PROTECT`** — `CustomerEmail`/`CustomerPhone`/`CustomerEntity` all use `PROTECT`, meaning hard-deleting a `Customer` will always fail while any of these exist. Soft-delete (via `BaseModel.delete()`) is the expected path.
  - **`PREFERNCE_TYPE_VALIDATOR` typo** — worth fixing in a coordinated rename before more apps depend on it.

- **Testing notes:** Not yet documented — to be filled in once factories/fixtures for `Customer` and related models exist.

- **TODOs / planned follow-ups:**
  - Per-app `Protocol` classes (platform-wide planned follow-up) for static typing of the `crm.Customer` contract.
  - `checks.py` once consuming apps are built and a formal `REQUIRED_CRM_CUSTOMER_ATTRS` contract is locked in.
  - Build the `Lead`, `Pipeline`, `Stage`, `Deal`, `DealStageHistory`, `CustomerAddress` models per HLD.

- **Changelog:**
  - 2026-07-15 — Corrected LLD to match actual implementation: replaced Lead/Pipeline/Stage/Deal descriptions with the real model set (CustomerEmail, CustomerPhone, CustomerEntity, PreferenceTypeValidator, CustomerPreferenceType, CustomerPreference); corrected directory structure; documented app_settings; added PREFERNCE_TYPE_VALIDATOR typo gotcha.
  - 2026-07-14 — Initial LLD (described HLD-planned models, not yet reflecting actual code).
