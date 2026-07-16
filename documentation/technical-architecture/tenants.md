# HLD: Multi-Tenancy Core (Tenants App)

> Location: `documentation/technical-architecture/tenants.md` <br/>
> Status: `Draft` <br/>
> Owner: Gurjot <br/>
> Last updated: 2026-07-15 <br/>
> Related BRD: N/A — foundational infrastructure, no BRD (not a client-facing feature) <br/>
> Related ADRs: None yet — point decisions folded into "Alternatives considered" below per platform convention (no ADR template exists yet) <br/>
> Implementing app(s): `backend/apps/tenants/README.md` (LLD — pending) <br/>

---

## What

The `tenants` app is the schema-based multi-tenancy core, built on `django-tenants`. It owns tenant identity (`Tenant`), hostname routing (`Domain`), a placeholder for per-tenant UI customization (`TenantBranding`), and per-tenant freeform configuration storage (`TenantConfiguration`). It lives entirely in the public schema (`SHARED_APPS`) and is a prerequisite for every tenant-schema app in the platform — nothing else can run without it.

This app explicitly does **not** cover: the module/feature-flag registry (owned by the `setup` app's `Configurations` model — see Alternatives), per-app swappable-FK targets (owned by `config.settings.base_models`, an unrelated pattern), or any tenant-schema business data.

## Why

- Every tenant-schema app (`crm`, `ledger`, `donation_management`, etc.) depends on schema-based isolation existing and working correctly first — this is load-bearing infrastructure, not a feature.
- Without an explicit `is_active` / soft-delete distinction, tenant deactivation and tenant schema teardown would be conflated into one flag, risking accidental data loss.
- The platform already has a swappable-FK convention for cross-app model references (`CRM_CUSTOMER`-style). This HLD exists partly to draw a clear line: tenant isolation is a **different mechanism** (physical schema separation) and must not be retrofitted into that pattern.

## How

**Components involved:**
- `tenants` app (public schema, `SHARED_APPS`) — owns `Tenant`, `Domain`, `TenantBranding`, `TenantConfiguration`.
- `django-tenants` library — supplies `TenantMixin` / `DomainMixin`, schema routing middleware, `TENANT_MODEL` / `TENANT_DOMAIN_MODEL` settings.
- `setup` app (separate, public schema) — owns the module/feature-flag registry (`Configurations` model), referenced but not owned here.
- Celery — used for asynchronous schema creation, not `core.app_settings` (that pattern doesn't apply to this app).

**Data flow:**
Tenant record created → schema provisioning deferred to a Celery task (not synchronous on `.save()`) → `Domain` record(s) registered against the tenant, one marked `is_primary` → incoming request's hostname resolved against `Domain.domain` by django-tenants middleware → matching tenant's schema activated for the request → tenant-scoped apps (`crm`, `ledger`, etc.) operate within that schema for the request's lifetime.

**Key models / contracts:**
- `Tenant` — subclasses `TenantMixin` (provides `schema_name`). Adds `name`, `public_id` (short human-readable identifier, distinct from the UUID PK — used in URLs/support contexts), `is_active` (usability switch, deliberately separate from `SoftDeleteMixin.is_deleted`, which signals "queued for schema teardown"). Mixins: `SafeModelMixin`, `SoftDeleteMixin`, `TimestampMixin`.
- `Domain` — subclasses `DomainMixin` (provides `domain`, `tenant` FK, `is_primary` — do not redeclare these). Adds `label` (human-friendly display name, e.g. "Production" vs. the raw hostname). `domain` is globally unique (hostname routing depends on it). Mixins: `SafeModelMixin`, `SoftDeleteMixin`, `TimestampMixin`.
- `TenantBranding` — abstract placeholder, no concrete fields yet; deferred until UI requirements are defined.
- `TenantConfiguration` — `name`, `label`, `details` (JSON), `tenant` (FK), `unique_together = (tenant, name)`. Mixins: `SafeModelMixin`, `SoftDeleteMixin`, `TimestampMixin`, `VersionedBetterModelMixin`. Scope: freeform per-tenant settings only — **not** module/feature-flag storage.

**Integration points:**
- `django-tenants` `SHARED_APPS` / `TENANT_APPS` split; `TENANT_MODEL` / `TENANT_DOMAIN_MODEL` settings point at this app's `Tenant` / `Domain`.
- Celery, for async schema creation on tenant provisioning.
- `setup` app's `Configurations` model, for Layer 2 module feature-flagging (per platform's 3-layer flagging design) — cross-referenced, not implemented here.

**Alternatives considered:**
- *Row-based `tenant_id` FK on every model* — rejected; contradicts the schema-isolation approach already adopted platform-wide.
- *Treating `Tenant` as a swappable-FK target like `CRM_CUSTOMER`* — rejected; schema isolation solves a different problem than pluggable identity models. Applying the swappable-FK pattern here would misrepresent the isolation mechanism and invite tenant-schema apps to wrongly add a `tenant` FK column.
- *Merging `TenantConfiguration` into the `setup` app's `Configurations` model* — rejected; kept as two distinct models. `TenantConfiguration` = freeform, versioned, per-tenant settings. `setup.Configurations` = structured, indexed module/feature-flag registry queried on every permission check.
- *Synchronous schema creation inside `Tenant.save()`* — rejected in favor of deferring to the platform's existing Celery backbone, to avoid blocking tenant-provisioning requests on DDL execution.

## Directory Structure

```
backend/apps/tenants/     # Tenant, Domain, TenantBranding, TenantConfiguration — public schema only, SHARED_APPS
backend/apps/setup/       # module/feature-flag registry (Configurations) — referenced, not owned here
```

## Miscellaneous

- Open questions: exact `public_id` format (slug vs. short code) not yet decided; `TenantBranding` concrete shape deferred until UI requirements land; Celery task design for async schema creation belongs in the LLD.
- Rollout: no feature flag — this app is foundational and always active, and precedes every other app in provisioning order.
- Non-functional: schema creation is a DDL operation and must never run inside a request/response cycle for real tenant provisioning; `Domain.domain` uniqueness is security-relevant (hostname routing) and must be enforced at the DB level, not just app-level validation.
- Changelog: 2026-07-15 — initial draft.