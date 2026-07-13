# LLD: `crm`

> Location: `backend/apps/crm/README.md` <br/>
> Status: `Active` <br/>
> Owner: <name> <br/>
> Last updated: 2026-07-14 <br/>
> Implements HLD: [`documentation/technical-architecture/crm.md`] <br/>
> Related ADRs: None <br/>

---

## What

`crm` owns the platform's canonical identity model, `crm.Customer`, along with the sales/donor-cultivation domain built on top of it: `Lead`, `Pipeline`/`Stage`, and `Deal`. `crm.Customer` fully replaces the old, project's original `Customer`/`Counterparty` model — this is a fresh start, no data migration from that model. This app is the **source** of the swappable identity reference every other app consumes (`notification_app`, `ledger`, `donation_management`, `expense_management`) — it does not itself define a `CRM_CUSTOMER`-style setting, because it has no need to swap out its own canonical model. What it does _not_ cover: the hand-off from a Won `Deal` into a `Donation` or `Invoice` — that boundary is intentionally still open (see Miscellaneous).

## Why

Both client types this platform serves — NGOs running donor cultivation, and SMBs running prospect-to-customer sales — need the same underlying shape: track a person or organization, move them through stages, eventually convert them into a paying/giving relationship. Rather than let `donation_management` and a future SMB sales app each invent their own version of "a contact," this app owns that identity once, and every other app references it through the swappable-FK convention rather than importing it directly. This keeps `crm` reusable as a standalone app across projects that may not need the Lead/Pipeline/Deal layer at all — a project could theoretically consume just `crm.Customer` via the swappable reference without installing the rest of this app's sales-pipeline models, though that's not the platform's current configuration.

## Python / Django Concepts

### `on_delete` behavior, specifically `PROTECT`

**What it is:** Every `ForeignKey` needs an `on_delete` argument telling Django what to do to rows that reference a target row when that target gets deleted. `CASCADE` deletes the referencing rows too; `SET_NULL` nulls the FK; `PROTECT` raises `ProtectedError` and refuses the delete outright if any referencing rows exist.

**Why this app needs it:** `Lead.converted_customer` uses `PROTECT` — once a `Lead` has converted into a `Customer`, that `Customer` cannot be deleted while the `Lead` record referencing it still exists, because doing so would silently sever the audit trail of "which lead became which customer." `PROTECT` is what turns "someone accidentally deletes a converted customer" from silent data loss into a loud, immediate error.

**Minor example:** `models.ForeignKey(Customer, on_delete=models.PROTECT)` — attempting `customer.delete()` while a `Lead` still points at it via this field raises `ProtectedError` instead of succeeding.

**The open question this creates:** `PROTECT` only stops a _hard_ delete. If this project wants `Customer` records to ever be removable at all (e.g. GDPR-style deletion requests, or routine cleanup), `PROTECT` implies you need a **soft-delete** path instead — mark the row inactive rather than actually deleting it — because a hard delete will always be blocked as long as history exists. This is flagged as an open decision below, not yet resolved.

### Concrete (single-table) inheritance vs. Multi-Table Inheritance (MTI)

**What it is:** Django offers MTI — a child model with its own base class creates a separate DB table joined via an implicit `OneToOneField` to the parent's table — as one way to model "a specialized version of X." The platform-wide alternative used here is a single concrete table per real-world entity, with variation captured in fields (like a `sub_type`/`stage` choice field) rather than a class hierarchy.

**Why this app needs it:** `Customer` needs to represent both an NGO donor and an SMB prospect without becoming two different database tables that both need joining back together for any cross-cutting query (e.g. "all customers created this month," regardless of client type). A single table keeps that trivial; MTI would mean every such query needs a join, and every migration touching a shared field needs to consider both tables. This is a platform-wide rule (see the Anti-patterns section below), not specific to this app, but `Customer`/`Lead`/`Deal` are exactly the kind of "same entity, different flavor" case MTI looks tempting for.

## LLD Concepts

### Being the _source_, not a _consumer_, of a swappable reference

**The pattern:** The plain string target, `CRM_CUSTOMER = "crm.Customer"`, is declared once, centrally, in `config.settings.base_models` — not inside `crm` and not duplicated inside each consuming app's own `app_settings.py`. Each consuming app that needs the resolved class form declares its own `LazyModelImport` field in its `app_settings.py`, pointing at that central string, with an accompanying `checks.py` validating the resolved model exposes what that consumer needs. `crm` itself declares neither — it doesn't need a swappable reference to its own model.

**Why this app follows it:** Swappable references exist to let a _consuming_ app be redirected at a _different_ target model by project override — that's meaningless for the app that defines the canonical model in the first place. `crm.Customer` is simply `crm.Customer`; there's nothing to swap it for from `crm`'s own point of view. Understanding this distinction matters because it's easy to assume, by analogy with every consumer app you've seen, that `crm` must have a `CRM_CUSTOMER` setting somewhere too — it doesn't, on purpose.

### The runtime contract, not the schema, is what other apps depend on

**The pattern:** Consuming apps don't import `crm.Customer` and inspect its fields directly. They declare `REQUIRED_CRM_CUSTOMER_ATTRS` (currently `id`, `display_name`, `email`, `phone`) and validate the swapped-in target actually exposes those, via `core.contracts.missing_attrs` and a `checks.py` system check — using `model._meta.get_field(name)` for real fields and `hasattr()` for methods/properties. This means `crm.Customer` is free to have far more fields than any single consumer needs, as long as the ones each consumer declared as required stay present.

**Why this app follows it:** This is what actually makes `crm.Customer` swappable in practice, not just in principle — a project can substitute a different customer model entirely, and as long as the substitute satisfies each consumer's declared attribute contract, nothing downstream breaks. It also means changes to `crm.Customer` that don't touch a currently-required attribute are safe to make freely; changes that _would_ remove or rename a required attribute are a cross-app breaking change, and the `checks.py` system checks are what catch that at `manage.py check` time rather than at some unpredictable runtime failure in a consuming app.

### Feature-agnostic core, feature-gated consumers

**The pattern:** `crm`'s models (`Customer`, `Lead`, `Pipeline`/`Stage`, `Deal`) don't themselves know or care whether a given tenant is an NGO or SMB — that distinction lives in how _consuming_ apps interpret and gate on the data, not in `crm`'s own schema beyond whatever `sub_type`-style discriminator fields are needed for concrete-table variation (see Concepts above).

**Why this app follows it:** Keeping client-type-specific behavior out of `crm` itself is what lets the same `Lead`→`Deal` pipeline serve donor cultivation and sales prospecting without `crm` needing to know about either domain's downstream logic (tax receipts vs. invoices). The feature-gating itself belongs to the platform's 3-layer flag system, not to this app.

## Anti-patterns

**Using Multi-Table Inheritance to model NGO vs. SMB customers as subclasses.**
_What it looks like:_ `class NGODonor(Customer): ...` and `class SMBProspect(Customer): ...`, each with their own table, relying on Django's automatic parent-join.
_Why it's wrong:_ This is the platform's golden rule violation — every cross-type query needs a join back to the base table, migrations affecting shared fields now touch multiple tables, and it directly contradicts the "single concrete table" decision already locked in for this project.
_Do instead:_ A `sub_type` (or similarly-named) choice field on the single `Customer` table, with behavior differences handled in application logic or consuming apps, not in the schema.

**A consuming app importing `from apps.crm.models import Customer` directly.**
_What it looks like:_ Any direct import of `crm`'s model from another app's `models.py`, `signals.py`, or elsewhere, instead of going through that app's own `app_settings.py` swappable reference.
_Why it's wrong:_ It hardcodes the dependency, defeating the entire point of the swappable-FK pattern — a project can no longer redirect that consumer at a different customer model without editing its source code, and `crm` can no longer be omitted or replaced in a project that doesn't want this specific identity model.
_Do instead:_ Declare a `LazyModelImport` in the consuming app's own `app_settings.py`, pointing at the central string in `config.settings.base_models`, per the "Being the source, not a consumer" concept above.

**Assuming a required attribute is safe to remove from `Customer` because nothing in `crm` itself uses it.**
_What it looks like:_ Deleting or renaming a field on `Customer` based only on checking `crm`'s own code for references.
_Why it's wrong:_ The actual dependency surface is every consuming app's declared `REQUIRED_CRM_CUSTOMER_ATTRS`, which `crm` has no direct visibility into without running (or reasoning about) those apps' own `checks.py`. A field can look "unused" from inside `crm` while several other apps' system checks would immediately start failing.
_Do instead:_ Treat every consuming app's `REQUIRED_*_ATTRS` list as the actual contract surface before changing or removing any field — grep for `REQUIRED_CRM_CUSTOMER_ATTRS` across the codebase, don't rely on `crm`'s own usage as the signal.

## How

- **Models:**
  - `Customer` — canonical identity model, both NGO donor and SMB prospect representations live here on one concrete table.
  - `Lead` — pre-conversion prospect/donor-candidate; `converted_customer` is a `ForeignKey(Customer, on_delete=PROTECT)` — see Concepts above for why `PROTECT` specifically, and the soft-delete question it raises.
  - `Pipeline` / `Stage` — the ordered stages a `Deal` moves through; scoped to allow different pipelines for different flows (donor cultivation vs. SMB sales) without `crm` needing to hardcode either.
  - `Deal` — the in-flight opportunity tied to a `Customer`, moving through a `Pipeline`'s `Stage`s toward Won/Lost.
- **Swappable settings:** none defined by `crm` itself (see LLD Concepts — this app is the source, not a consumer). The plain `CRM_CUSTOMER = "crm.Customer"` string lives centrally in `config.settings.base_models`; consuming apps that need the resolved class declare their own `LazyModelImport` in their `app_settings.py`, pointing at that central string.
- **Contracts / checks:** `crm` doesn't validate its own model against a `REQUIRED_*_ATTRS` list (nothing to validate against itself) — but it is the implicit contract every consuming app's checks validate against. Current baseline contract, per those consumers: `id`, `display_name`, `email`, `phone`. Whether this needs to expand is an open question (see Miscellaneous).
- **Migrations:** fresh-start migrations for `Customer`/`Lead`/`Pipeline`/`Stage`/`Deal` — no data migration from the old `Customer`/`Counterparty` model, which is deleted outright rather than migrated.
- **Signals / side effects:** the Won-`Deal` → `Donation`/`Invoice` hand-off is not yet implemented — whether this is signal-driven (a `Deal` status change firing a signal that `donation_management`/a future invoicing app listens for) or explicitly orchestrated some other way is one of the open questions below.
- **API surface:** not yet finalized in this doc — to be filled in once the DRF serializers/views layer for CRM is built.
- **Gotchas:**
  - Don't assume `crm` needs a `CRM_CUSTOMER` setting just because every consumer has one — it doesn't, by design (see LLD Concepts).
  - `Lead.converted_customer`'s `PROTECT` means bulk-delete tooling (admin actions, cleanup scripts) that touches `Customer` rows will start raising `ProtectedError` the moment any of those customers have an associated converted `Lead` — this is expected, not a bug, but worth knowing before writing any delete-adjacent tooling.

## Directory Structure

```
backend/apps/crm/
├── models.py         # Customer, Lead, Pipeline, Stage, Deal
├── migrations/
├── serializers.py       # not yet finalized
├── views.py            # not yet finalized
├── admin.py
└── README.md            # this file
```

## Miscellaneous

- **Open questions (carried over from the BRD/HLD, not yet decided):**
  - **Won-Deal → Donation/Invoice hand-off mechanism.** Signal-driven vs. explicitly orchestrated by the consuming app; affects whether `crm` needs to expose any hook at all, or whether this lives entirely outside `crm`.
  - **Whether `REQUIRED_CRM_CUSTOMER_ATTRS` needs to expand** beyond `id`/`display_name`/`email`/`phone` — likely to surface as consuming apps (`donation_management`, a future invoicing app) get built out and discover they need more than the current baseline.
  - **Soft-delete dependency implied by `Lead.converted_customer`'s `PROTECT`.** If `Customer` records need to be removable at all, this app will need a `SoftDeleteMixin`-style pattern (consistent with the platform's existing mixin conventions) rather than relying on hard deletes ever succeeding once a `Lead` conversion exists.
- **Testing notes:** not yet documented — to be filled in once factories/fixtures for `Customer`/`Lead`/`Deal` exist.
- **TODOs / planned follow-ups:** per-app `Protocol` classes (platform-wide planned follow-up) scoped to what each consumer of `crm.Customer` actually touches, as a static-typing layer on top of the runtime `REQUIRED_*_ATTRS` checks.
- **Changelog:**
  - 2026-07-14 — Initial LLD, guide-style with Concepts/Anti-patterns sections.
