# LLD: `<app_name>`

> Location: `backend/apps/<app_name>/README.md` <br/>
> Status: `Active | Deprecated` <br/>
> Owner: <name> <br/>
> Last updated: <date> <br/>
> Implements HLD: [<link to documentation/technical-architecture/...>] <br/>
> Related ADRs: [<links>] <br/>

---

## What

What this app is responsible for, in concrete terms — its models, the domain it owns, and its boundary with sibling apps. If this app implements part of a larger HLD, say which part.

## Why

Why this app exists as a separate app rather than living inside another one (bounded context, reuse across projects, feature-gating, etc.). Link to the HLD for the broader rationale.

## How

Implementation details a developer needs before touching this code.

- **Models:** key models, their fields of note, and any non-obvious constraints.
- **Swappable settings:** any `app_settings.py` swappable FK targets and their `project_settings` override keys.
- **Contracts / checks:** `REQUIRED_*_ATTRS`, `checks.py` system checks, and what they validate.
- **Migrations:** anything non-standard (e.g. `swappable_dependency()` usage, data migrations).
- **Signals / side effects:** what triggers what, and where.
- **API surface:** key endpoints/serializers this app exposes, if any.
- **Gotchas:** known sharp edges, footguns, or things that look wrong but aren't.

## Directory Structure

```
backend/apps/<app_name>/
├── models.py
├── app_settings.py       # swappable FK targets
├── checks.py             # system checks against swappable target
├── migrations/
├── serializers.py
├── views.py
├── signals.py
├── tasks.py               # if Celery tasks exist
└── README.md              # this file
```

Adjust to actual structure — remove files that don't exist, add ones that do.

## Miscellaneous

- Testing notes (fixtures, factories, anything non-obvious about the test setup).
- TODOs / planned follow-ups (e.g. Protocol classes, deferred refactors).
- Changelog of major revisions to this doc.
