# BRD: <Feature / Initiative Name>

> Location: `documentation/business-requirement-documents/<feature-name>.md` <br/>
> Status: `Draft | Proposed | Approved | Superseded` <br/>
> Owner: <name> <br/>
> Last updated: <date> <br/>
> Related HLD: [<link to documentation/technical-architecture/...>] <br/>
> Target client type / tenant(s): <e.g. NGO / SMB / Personal> <br/>

---

## What

Plain-language description of the feature from a product/user point of view — no implementation detail. What does the user get, what can they now do that they couldn't before.

## Why

- Business problem or opportunity driving this.
- Who asked for it / which client type or use case motivates it.
- Impact of not building it (lost client, manual workaround cost, competitive gap, etc.).
- Success metric(s) — how we'll know this worked.

## How

Describes the feature from the *user's* journey, not the system's internals — that belongs in the linked HLD.

- **User(s) / persona(s):** who interacts with this (donor, admin, accountant, anonymous public user, etc.).
- **User flow:** step-by-step of how the persona uses the feature, end to end.
- **Scope:** what's in scope for this iteration.
- **Out of scope:** explicitly called out — prevents scope creep and sets expectations for what's deferred.
- **Acceptance criteria:** concrete, testable conditions that define "done."

## Directory Structure

Optional — only include if the BRD needs to reference which parts of the product surface (screens/modules) are affected, not code structure:

```
Donation Portal (public)     → new
Admin Dashboard → Campaigns  → new
Admin Dashboard → Reports    → modified
```

Omit this section if not useful for the feature.

## Miscellaneous

- Open questions for stakeholders.
- Dependencies on other features/BRDs.
- Rollout / phasing notes (e.g. NGO first, SMB later).
- Changelog of major revisions to this doc.