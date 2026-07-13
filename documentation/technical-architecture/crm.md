# HLD: Customer Relationship Management (CRM)

> Location: `documentation/technical-architecture/crm.md` <br/>
> Status: `Draft` <br/>
> Owner: <name> <br/>
> Last updated: 2026-07-12 <br/>
> Related BRD: [documentation/business-requirement-documents/crm.md] <br/>
> Related ADRs: [ADR — Swappable Cross-App FK Pattern (existing)] <br/>
> Implementing app(s): [backend/apps/crm/README.md] <br/>

---

## What

`apps.crm` is the tenant-schema app that owns identity (`Customer`, `CustomerAddress`) and a lightweight sales/relationship engine (`Lead`, `Pipeline`, `Stage`, `Deal`) for the platform. It becomes the **single canonical identity source** consumed by every other tenant-schema app via the platform's swappable-FK pattern. This HLD covers the CRM app's own design and the contract it exposes to consumers. It does **not** cover the internal design of consuming apps (Donations, Invoicing, Notifications, Expenses) beyond the shape of their `CRM_CUSTOMER` swappable reference — those live in their own LLDs.

## Why

- The platform currently has customer identity duplicated/informally reused across apps (see architecture summary — old `Customer`/`Counterparty`). This blocks cross-module reporting and forces every app to define its own notion of "who."
- SMB expansion (Phase 2 of the platform roadmap) requires a sales pipeline that doesn't exist yet — Leads and Deals must exist before an Invoice can be generated for a new customer.
- Full BRD rationale: see linked BRD.

## How

### Components involved
- **`apps.crm`** — owns `Customer`, `CustomerAddress`, `Lead`, `Pipeline`, `Stage`, `Deal`. Exposes `crm.Customer` as the concrete model other apps reference.
- **`apps.notification_app`, `apps.ledger`, `apps.donation_management`, `apps.expense_management`** — each defines its own `CRM_CUSTOMER = 'crm.Customer'` swappable setting in their `app_settings.py`, resolved at runtime, never importing `crm.models.Customer` directly.
- **`core.contracts`** — supplies the existing `missing_attrs()` primitive used by every consuming app's `checks.py` to validate that whatever model is swapped in for `CRM_CUSTOMER` satisfies that app's `REQUIRED_CRM_CUSTOMER_ATTRS`.
- **Existing DAG Seeder** — seeds a default `Pipeline` + `Stage` set per tenant client-type (NGO: donor-cultivation pipeline; SMB: sales pipeline) at tenant provisioning time.

### Data flow
1. A human (staff/rep) or another app creates a `Customer` directly, or indirectly via `Lead` conversion.
2. A `Lead` is qualified and converted → creates/links a `Customer`, creates a `Deal` in the tenant's default `Pipeline` at its first `Stage`.
3. `Deal` moves through `Stage`s (ordered, per `Pipeline`); each stage transition is logged (`DealStageHistory`) for audit.
4. On `Deal.status = won`, the `Customer` is now available for consuming apps — `apps.invoicing`/`apps.donation_management` pick it up via their own flows (out of scope here; this HLD stops at "Customer exists and is queryable").
5. Every consuming app resolves `Customer` at runtime via `django.apps.apps.get_model(*settings.CRM_CUSTOMER.split('.'))` (or equivalent resolution helper already established by the platform pattern) rather than a hardcoded import.

```
Lead ──(convert)──> Customer ──┬──> Deal ──(stage transitions)──> Won/Lost
                                │
                                ├──> consumed by apps.donation_management (Donation.donor)
                                ├──> consumed by apps.ledger (JournalLineItem counterparty, if applicable)
                                ├──> consumed by apps.expense_management (ExpenseReceipt.vendor)
                                └──> consumed by apps.notification_app (NotificationLog.recipient)
```

### Key models / contracts
- **`Customer`** (`SafeModelMixin`, `VersionedBetterModelMixin`, `TimestampMixin`, `SoftDeleteMixin`): `sub_type` (`individual` | `organization` | `anonymous`), `display_name`, `email` (nullable), `phone` (nullable), `organization_name` (nullable, populated when `sub_type=organization`).
- **`CustomerAddress`**: FK to `Customer`, standard address fields, `is_primary`.
- **`Lead`**: pre-Customer prospect — `name`, `email`, `phone`, `source`, `status` (`new`/`qualified`/`disqualified`/`converted`), `converted_customer` (nullable FK to `Customer`, set on conversion), `owner` (FK to `AUTH_USER_MODEL`).
- **`Pipeline`**: `name`, `is_default`, tenant-scoped.
- **`Stage`**: FK to `Pipeline`, `name`, `order`, `is_won_stage`, `is_lost_stage`.
- **`Deal`**: FK to `Customer`, FK to `Pipeline`, FK to `Stage`, `amount` (`DecimalField`, matches platform's `max_digits=20, decimal_places=4` convention), `expected_close_date`, `status` (`open`/`won`/`lost`), `lost_reason` (nullable), `owner` (FK to `AUTH_USER_MODEL`).
- **`DealStageHistory`**: FK to `Deal`, `from_stage`, `to_stage`, `changed_by`, `changed_at` — audit trail for pipeline movement.
- **Contract exposed to consumers:** `CRM_CUSTOMER` swappable setting resolving to `crm.Customer` by default. Consuming apps declare `REQUIRED_CRM_CUSTOMER_ATTRS = ['id', 'display_name', 'email', 'phone']` (per-app, scoped to what they actually touch) and validate via their own `checks.py` + `missing_attrs()`.

### Integration points
- **Feature flags:** CRM's Lead/Pipeline/Deal UI is gated behind a `crm_pipeline` module flag (Layer 2, tenant config) — Customer identity itself is **not** gated (every tenant needs identity; only the sales-pipeline UI is optional, e.g. a pure donation-portal tenant may not need Leads/Deals surfaced).
- **Seeder DAG:** new DAG nodes for default `Pipeline`/`Stage` seeding per client type.
- **Notification system:** future event types (`DEAL_WON`, `DEAL_STAGE_CHANGED`) can be added to `NotificationTemplate` — not built in this iteration, but the `Deal` model's stage-transition points are designed to make adding signals trivial later.

### Alternatives considered
- **Generic Foreign Key for Customer references (instead of swappable concrete FK):** rejected — breaks the platform's established "swappable FK, not GFK" convention (already decided per architecture summary), loses referential integrity and query performance, and complicates system checks.
- **Multi-Table Inheritance for `Lead`/`Deal` per client type (NGO vs SMB):** rejected per the platform's Golden Rule — single concrete tables, feature flags/UI dictate what's shown, not the schema.
- **One global Pipeline shared across all tenants:** rejected — Pipelines must be tenant-scoped and seedable per client type (NGO donor-cultivation stages differ meaningfully from SMB sales stages).

## Directory Structure

```
backend/apps/crm/          # identity + leads + pipeline + deals; source of CRM_CUSTOMER
backend/apps/notification_app/   # consumes CRM_CUSTOMER, no schema change beyond FK target swap
backend/apps/ledger/             # consumes CRM_CUSTOMER where a counterparty is needed
backend/apps/donation_management/# consumes CRM_CUSTOMER as Donation.donor
backend/apps/expense_management/ # consumes CRM_CUSTOMER as ExpenseReceipt.vendor
frontend/src/modules/crm/        # Customers, Leads, Pipeline board, Deals UI
```

## Miscellaneous

- **Open questions / known unknowns:**
  - Exact `REQUIRED_CRM_CUSTOMER_ATTRS` per consuming app — needs a pass once each app's actual usage of Customer fields is audited (tracked as a follow-up, ties into the platform's planned per-app `Protocol` classes).
  - Won-Deal → Donation/Invoice hand-off mechanism (signal vs explicit action) — deferred, not blocking this HLD.
  - Duplicate Customer detection/merge — flagged in BRD as near-future, not designed here.
- **Rollout plan:** Single-phase rollout since this is a fresh project — `apps.crm` ships alongside the cutover of all consuming apps to `CRM_CUSTOMER` in the same release. Feature flag: `crm_pipeline` (Layer 2 tenant config) gates only the Lead/Pipeline/Deal UI, not identity.
- **Non-functional considerations:**
  - **Multi-tenancy:** all CRM models live in tenant schema (via `django-tenants`); no cross-tenant leakage risk beyond what the existing tenant-schema isolation already guarantees.
  - **Performance:** `Deal` list/board views should be indexed on `(pipeline_id, stage_id)` for kanban-style queries; `Customer` indexed on `sub_type` and `email`.
  - **Security:** Lead/Deal ownership (`owner` FK) should be respected in permission classes — a rep should not see another rep's Leads unless granted via Layer 3 (Groups/Permissions), per the platform's existing 3-layer feature-flag/permission model.
- **Changelog:**
  - 2026-07-12 — Initial draft.