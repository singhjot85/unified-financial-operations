# BRD: Customer Relationship Management (CRM)

> Location: `documentation/business-requirement-documents/crm.md` <br/>
> Status: `Draft` <br/>
> Owner: <name> <br/>
> Last updated: 2026-07-12 <br/>
> Related HLD: [documentation/technical-architecture/crm.md] <br/>
> Target client type / tenant(s): NGO (immediate), SMB (near-future), Personal (indirect — vendor tracking) <br/>

---

## What

A single, canonical place to know **who we deal with** and **where each relationship stands**. The CRM app owns identity for every person or organization the platform interacts with — donors, customers, vendors, prospects — and adds a lightweight sales/relationship engine on top: Leads that haven't converted yet, and Deals moving through a Pipeline toward a won/lost outcome.

Every other module (Donations, Invoicing, Notifications, Expenses) stops maintaining its own notion of "who this money belongs to" and instead points at a CRM Customer. This BRD covers identity + lead capture + pipeline/deal tracking. It does **not** cover marketing automation, email campaigns, or third-party CRM sync (Salesforce/HubSpot) — those are out of scope for this iteration.

## Why

- Today, customer identity is duplicated/ambiguous across apps (an old `Customer`/`Counterparty` model was being reused informally for donors, invoice clients, and vendors). This causes data drift and makes cross-module reporting ("total lifetime value of this person across donations + invoices") impossible without manual joins.
- The NGO client needs to track donor relationships beyond a single transaction — repeat donors, major-gift prospects, corporate sponsors moving through a cultivation pipeline.
- The upcoming SMB client type needs a real sales pipeline (Lead → Deal → Won) before invoicing even begins — invoicing today assumes the customer already exists, but SMBs need to manage the sales conversation first.
- Not building this means every future app keeps re-inventing "who is this," identity data stays fragmented per app, and there's no way to do org-wide relationship reporting.
- **Success metric(s):**
  - 100% of new Donations, Invoices, and Expense vendor records resolve to a `crm.Customer` (zero orphaned identity records in other apps).
  - An SMB tenant can take a prospect from Lead → Won Deal → first Invoice without leaving the CRM + Invoicing UI.
  - Old `Customer`/`Counterparty` model fully removed from the codebase with no functional regression.

## How

- **User(s) / persona(s):**
  - **Org Admin / Staff** — creates and manages Customers, Leads, Deals; moves deals through pipeline stages.
  - **Sales/Development Rep** (SMB, or NGO major-gifts officer) — owns a portfolio of Leads/Deals, works them through the pipeline.
  - **System (internal)** — other apps (Donations, Invoicing, Notifications, Expenses) read/write Customer records via the swappable-FK contract; not a human persona, but a first-class consumer of this app's data.

- **User flow (NGO — donor becomes major-gift prospect):**
  1. A one-time anonymous donation comes in; system auto-creates a minimal `Customer` (sub_type=`anonymous` or `individual`) if the donor left contact info.
  2. Development officer spots a repeat donor and manually promotes them: creates a `Lead` (or directly a `Deal` if pipeline is skipped for individuals) tagged as "major-gift prospect."
  3. Officer moves the Deal through stages (`Identified` → `Cultivating` → `Ask Made` → `Won`/`Lost`) as the relationship develops.
  4. On `Won`, the platform can optionally trigger a follow-up (e.g., notification, or hand-off to Donation module) — but this hand-off is out of scope for this BRD, it's a future integration point.

- **User flow (SMB — prospect to customer):**
  1. Rep creates a `Lead` from an inbound inquiry (name, org, contact info, source).
  2. Rep qualifies the Lead and converts it into a `Deal` attached to a `Customer` (Customer is created on conversion if it doesn't exist).
  3. Deal moves through Pipeline stages (`New` → `Qualified` → `Proposal` → `Negotiation` → `Won`/`Lost`).
  4. On `Won`, the Customer now exists and is ready to be invoiced by `apps.invoicing` — no CRM-side action required beyond the Customer record existing.

- **Scope (this iteration):**
  - Customer identity model (replacing old Customer/Counterparty), with `sub_type` (`individual` / `organization` / `anonymous`).
  - Customer addresses (reuse existing `CustomerAddress` pattern).
  - Lead capture and qualification.
  - Pipeline + Stage configuration (tenant-configurable stages, at least one default pipeline seeded per tenant type).
  - Deal tracking through a Pipeline, with amount, expected close date, owner, won/lost outcome.
  - Every consuming app (Donations, Invoicing, Notifications, Expenses) updated to reference `crm.Customer` via the swappable-FK pattern instead of the old model.

- **Out of scope:**
  - Marketing automation / email drip campaigns.
  - Third-party CRM sync (Salesforce, HubSpot, etc.).
  - Automatic Lead-to-Deal-to-Donation/Invoice hand-off logic (this is a future integration, tracked separately).
  - Duplicate-detection / merge tooling for Customers (flagged as a near-future need, not this iteration).
  - Multiple pipelines per tenant with custom stage builders in the UI (this iteration ships with tenant-configurable stages via admin/config, not a drag-and-drop pipeline builder).

- **Acceptance criteria:**
  - [ ] A `Customer` can be created with `sub_type` in (`individual`, `organization`, `anonymous`), with `email`/`phone` nullable.
  - [ ] A `Lead` can be created independent of any Customer, and converting a Lead creates (or links to an existing) `Customer` and a `Deal`.
  - [ ] A `Deal` always belongs to exactly one `Pipeline` and one `Stage` within that pipeline; moving stages is auditable (who moved it, when).
  - [ ] A `Deal` can be marked `Won` or `Lost` with a reason; won/lost deals are locked from further stage changes.
  - [ ] `apps.donation_management`, `apps.expense_management`, `apps.notification_app`, and `apps.ledger` (where applicable) all resolve their customer-like FK through `crm.Customer` via the swappable-FK setting — zero hardcoded imports of `crm.Customer`.
  - [ ] Old `Customer`/`Counterparty` model and all references to it are removed from the codebase (this is a fresh project — no data migration required).
  - [ ] Multi-tenant isolation holds: no Customer/Lead/Deal is visible cross-tenant.

## Directory Structure

```
Admin Dashboard → CRM → Customers   → new
Admin Dashboard → CRM → Leads       → new
Admin Dashboard → CRM → Pipeline    → new
Admin Dashboard → CRM → Deals       → new
```

## Miscellaneous

- **Open questions for stakeholders:**
  - Should `anonymous` sub_type Customers ever be promoted to `individual` automatically (e.g., if they donate again with contact info), or is that always a manual merge?
  - Does the NGO tenant need a distinct default Pipeline ("Donor Cultivation") separate from the SMB default Pipeline ("Sales")? (Assumed yes — seeded per tenant type via the existing DAG Seeder, per Step 6 of the platform's implementation sequence.)
  - Who owns "Won" Deal → Donation/Invoice creation — is that a CRM signal, or does the receiving app poll/subscribe? (Deferred to HLD/near-future integration design.)
- **Dependencies:** Depends on the platform's swappable-FK + system-checks pattern already established (see architecture summary). Blocks: `apps.donation_management`, `apps.expense_management` cutover to the new identity model.
- **Rollout / phasing notes:** Ship CRM app first (identity + leads + pipeline + deals), then cut over consuming apps to `crm.Customer` in the same phase since this is a fresh project (no legacy data to migrate).
- **Changelog:**
  - 2026-07-12 — Initial draft.