# HLD: Customer Relationship Management (CRM)

> Location: `documentation/technical-architecture/crm.md` <br/>
> Status: `Draft` <br/>
> Owner: <name> <br/>
> Last updated: 2026-07-15 <br/>
> Related BRD: [documentation/business-requirement-documents/crm.md](../business-requirement-documents/crm.md) <br/>
> Related ADRs: [ADR — Swappable Cross-App FK Pattern (existing)] <br/>
> Implementing app(s): [backend/apps/crm/README.md](../../backend/apps/crm/Readme.md) <br/>

---

> **Implementation status:** The `Customer` identity layer and preference system (`CustomerEmail`, `CustomerPhone`, `CustomerEntity`, `CustomerPreferenceType`, `CustomerPreference`) are implemented. The sales/relationship layer (`Lead`, `Pipeline`, `Stage`, `Deal`, `DealStageHistory`, `CustomerAddress`) described in this HLD is **not yet built**.

## What

`apps.crm` is the tenant-schema app that owns identity (`Customer` and related sub-models) and a lightweight sales/relationship engine (`Lead`, `Pipeline`, `Stage`, `Deal`) for the platform. It becomes the **single canonical identity source** consumed by every other tenant-schema app via the platform's swappable-FK pattern. This HLD covers the CRM app's own design and the contract it exposes to consumers. It does **not** cover the internal design of consuming apps (Donations, Invoicing, Notifications, Expenses) beyond the shape of their `CRM_CUSTOMER` swappable reference — those live in their own LLDs.

## Why

- The platform currently has customer identity duplicated/informally reused across apps (see architecture summary — old `Customer`/`Counterparty`). This blocks cross-module reporting and forces every app to define its own notion of "who."
- SMB expansion (Phase 2 of the platform roadmap) requires a sales pipeline that doesn't exist yet — Leads and Deals must exist before an Invoice can be generated for a new customer.
- Full BRD rationale: see linked BRD.

## How

### Components involved
- **`apps.crm`** — owns `Customer`, `CustomerEmail`, `CustomerPhone`, `CustomerEntity`, `CustomerPreferenceType`, `CustomerPreference` (implemented); `CustomerAddress`, `Lead`, `Pipeline`, `Stage`, `Deal`, `DealStageHistory` (planned, not yet built). Exposes `crm.Customer` as the concrete model other apps reference.
- **`apps.notification_app`, `apps.ledger`, `apps.donation_management`, `apps.expense_management`** — each will define its own swappable `DefferedImport` setting in its `app_settings.py` pointing at `CRM_CUSTOMER` from `config.settings.base_models`, resolved at runtime, never importing `crm.models.Customer` directly. (These apps are not yet built.)
- **`core.contracts`** — supplies the existing `missing_attrs()` primitive used by every consuming app's `checks.py` to validate that whatever model is swapped in for `CRM_CUSTOMER` satisfies that app's `REQUIRED_CRM_CUSTOMER_ATTRS`.
- **Existing DAG Seeder** — will seed a default `Pipeline` + `Stage` set per tenant client-type at tenant provisioning time (not yet implemented).

### Data flow (planned)

1. A human (staff/rep) or another app creates a `Customer` directly, or indirectly via `Lead` conversion. _(Customer creation is implemented; Lead is not yet.)_
2. A `Lead` is qualified and converted → creates/links a `Customer`, creates a `Deal` in the tenant's default `Pipeline` at its first `Stage`. _(Not yet built.)_
3. `Deal` moves through `Stage`s (ordered, per `Pipeline`); each stage transition is logged (`DealStageHistory`) for audit. _(Not yet built.)_
4. On `Deal.status = won`, the `Customer` is now available for consuming apps — `apps.invoicing`/`apps.donation_management` pick it up via their own flows.
5. Every consuming app resolves `Customer` at runtime via its own `DefferedImport` setting in `app_settings.py`, pointing at `CRM_CUSTOMER` in `config.settings.base_models`.

```
Lead ──(convert)──> Customer ──┬──> Deal ──(stage transitions)──> Won/Lost
                                │
                                ├──> consumed by apps.donation_management (Donation.donor)
                                ├──> consumed by apps.ledger (JournalLineItem counterparty, if applicable)
                                ├──> consumed by apps.expense_management (ExpenseReceipt.vendor)
                                └──> consumed by apps.notification_app (NotificationLog.recipient)
```

### Key models / contracts

**Implemented:**
- **`Customer`** (`BaseModel`, `AbstractParty`): `party_type` (`individual` | `entity`), `customer_type` (`donor` | `bo` | `client`), `customer` (self-referential FK, nullable), `dob`, `user` (FK to `AUTH_USER`, nullable).
- **`CustomerEmail`**: FK to `Customer` (`PROTECT`), `is_primary`, `email`, `type` (primary/secondary/tertiary).
- **`CustomerPhone`**: FK to `Customer` (`PROTECT`), `is_primary`, `phone`, `type` (primary/secondary/tertiary).
- **`CustomerEntity`**: FK to `Customer` + `GenericForeignKey` to any other model (`entity_content_type` + `entity_object_id`).
- **`CustomerPreferenceType`**: defines a named preference key with `data_type` and `additional_meta_data` JSON (label, default, multi-select, choices).
- **`CustomerPreference`**: per-Customer value for a `CustomerPreferenceType`. Value stored in a `JSONField`.

**Planned (not yet built):**
- **`CustomerAddress`**: FK to `Customer`, standard address fields, `is_primary`.
- **`Lead`**: `name`, `email`, `phone`, `source`, `status`, `converted_customer` (nullable FK to `Customer`, `PROTECT`), `owner` (FK to `AUTH_USER`).
- **`Pipeline`**: `name`, `is_default`, tenant-scoped.
- **`Stage`**: FK to `Pipeline`, `name`, `order`, `is_won_stage`, `is_lost_stage`.
- **`Deal`**: FK to `Customer`, FK to `Pipeline`, FK to `Stage`, `amount`, `expected_close_date`, `status` (`open`/`won`/`lost`), `lost_reason`, `owner`.
- **`DealStageHistory`**: FK to `Deal`, `from_stage`, `to_stage`, `changed_by`, `changed_at`.

**Contract exposed to consumers:** `CRM_CUSTOMER` plain string (`"crm.Customer"`) in `config.settings.base_models`. Consuming apps declare a `DefferedImport` in their own `app_settings.py` pointing at that string, and validate the resolved model via `REQUIRED_CRM_CUSTOMER_ATTRS` in their `checks.py`.

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
backend/apps/crm/          # identity + preferences; source of CRM_CUSTOMER  [IMPLEMENTED]
backend/apps/notification_app/   # will consume CRM_CUSTOMER  [NOT YET BUILT]
backend/apps/ledger/             # will consume CRM_CUSTOMER where a counterparty is needed  [NOT YET BUILT]
backend/apps/donation_management/# will consume CRM_CUSTOMER as Donation.donor  [NOT YET BUILT]
backend/apps/expense_management/ # will consume CRM_CUSTOMER as ExpenseReceipt.vendor  [NOT YET BUILT]
frontend/src/modules/crm/        # Customers, Leads, Pipeline board, Deals UI  [NOT YET BUILT]
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
  - 2026-07-15 — Updated to reflect implementation status: Customer identity layer implemented; Lead/Pipeline/Stage/Deal planned but not yet built. Corrected model field names to match actual code (party_type/customer_type vs sub_type; no display_name field). Corrected consuming apps to use DefferedImport not DefferedModel.
  - 2026-07-12 — Initial draft.