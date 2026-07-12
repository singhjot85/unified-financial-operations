# Loosely-Coupled Django App Architecture

General pattern to apply across all apps in the platform. Minor tweaks allowed per app, but the core mechanism should stay consistent.
Swappable independent modules prferred over compile-time tight-coupled apps.

## Core Principle

Apps do not hardcode FKs to other apps' models. Instead, each app exposes **swappable model references** via its own `app_settings.py`, overridable per-project. This generalizes Django's own `AUTH_USER_MODEL` pattern to any cross-app foreign key — not just auth.

Coupling moves from *"app A imports app B's models"* to *"app A requires some model matching a declared shape to be configured."* This is not zero-dependency — it's swappable dependency, validated at boot time instead of import time.

---

## 1. `app_settings.py` — Swappable References

Each app declares its foreign references with defaults, resolved from project settings at import time.

```python
# notification_app/app_settings.py
from django.conf import settings

_overrides = getattr(settings, 'NOTIFICATION_APP_SETTINGS', {})

CRM_CUSTOMER = _overrides.get('CRM_CUSTOMER', 'crm.Customer')
```

```python
# notification_app/models.py
from .app_settings import CRM_CUSTOMER

class NotificationLog(...):
    party = models.ForeignKey(CRM_CUSTOMER, on_delete=models.CASCADE)
```

**Overriding in a different project:**

```python
# project_settings.py
NOTIFICATION_APP_SETTINGS = {
    "CRM_CUSTOMER": settings.AUTH_USER_MODEL,  # swap target entirely
}
```

This works because `django.conf.settings` is fully populated before `INSTALLED_APPS` models are imported during app-registry population — no circular import issue, same trick DRF uses for `REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES']`.

---

## 2. Migrations — `swappable_dependency()`

Migration history is **per-project**, not shared when the same app is reused across projects. A migration generated in Project A (target = `crm.Customer`) will bake in a wrong dependency if dropped into Project B (target = `auth.User`) unless the swap mechanism is used correctly.

Use Django's built-in helper instead of a raw string app dependency:

```python
dependencies = [
    migrations.swappable_dependency(app_settings.CRM_CUSTOMER),
]
```

Each project runs its own `makemigrations` after setting its overrides, producing its own migration history.

---

## 3. Runtime Contract Safety — System Checks

Since the FK target is only known at settings-resolution time, validate its shape at **Django boot time** (`manage.py check` / server start) rather than waiting for a rare code path to hit a missing attribute in production.

### Shared primitive (`core.contracts`)

```python
# core/contracts.py
def missing_attrs(obj, *attrs):
    """Pure check — returns list of missing attr names, no side effects."""
    return [a for a in attrs if not hasattr(obj, a)]
```

- Pure function. No raises, no side effects.
- Lives in a shared low-level utility app every app can depend on (this is a plain function, not a model — doesn't violate the no-cross-app-FK rule).

### Per-app system check

```python
# notification_app/checks.py
from django.apps import apps
from django.core.checks import Error, register
from core.contracts import missing_attrs
from .app_settings import CRM_CUSTOMER

REQUIRED_PARTY_ATTRS = ["get_display_name", "primary_email"]

@register()
def check_crm_customer_contract(app_configs, **kwargs):
    model = apps.get_model(CRM_CUSTOMER)
    missing = missing_attrs(model, *REQUIRED_PARTY_ATTRS)
    if missing:
        return [Error(
            f"{CRM_CUSTOMER} (configured via NOTIFICATION_APP_SETTINGS.CRM_CUSTOMER) "
            f"is missing required attribute(s): {', '.join(missing)}.",
            hint="Update the target model or NOTIFICATION_APP_SETTINGS override.",
            id="notification_app.E001",
        )]
    return []
```

### Conventions

- **Error id namespace:** `<app_label>.E00X`, sequential — matches Django's own convention (`auth.E001`, etc.), keeps ids greppable.
- **Return, never raise:** system checks must return `Error`/`Warning` objects. A raised exception crashes `manage.py check` itself instead of producing a clean report.
- **Fields vs. methods/properties:**
  - Fields: check via `model._meta.get_field(name)` in a try/except — `hasattr()` is not reliable for all field types on the class.
  - Methods/properties: plain `hasattr()` is fine.
- Each app declares its own `REQUIRED_*_ATTRS` list scoped to exactly what *that app* touches on the target — not a shared universal list.

---

## 4. Static Contract Safety — Protocols (Future Layer)

Once runtime shapes stabilize, add typing-level enforcement so a developer can't push code against a foreign reference without knowing its contract.

```python
# notification_app/contracts.py
from typing import Protocol

class NotificationPartyLike(Protocol):
    def get_display_name(self) -> str: ...
    primary_email: str | None
```

- **Scoped per consuming app, not one shared god-Protocol** — interface segregation. `notification_app` only declares what it touches (display name, email); `ledger` would declare its own Protocol for what it touches (soft-delete, versioning, etc.).
- Lives alongside the `app_settings.py` that declares the swappable key it corresponds to.
- This is additive on top of the system checks, not a replacement — system checks catch misconfiguration at boot/CI time in a running project; Protocols catch it at editor/type-check time during development.

---

## 5. Summary of Layers

| Layer | Mechanism | When it fires | Purpose |
|---|---|---|---|
| Reference resolution | `app_settings.py` + project override dict | Import time | Swap the target model per project |
| Migration linkage | `migrations.swappable_dependency()` | `makemigrations` | Correct per-project migration graph |
| Runtime contract | `core.contracts.missing_attrs` + `checks.py` | `manage.py check` / server boot | Fail loudly if swap breaks the shape |
| Static contract | Per-app `Protocol` classes | Editor / CI type-check | Catch contract violations before runtime |

## Architectural Index

- 