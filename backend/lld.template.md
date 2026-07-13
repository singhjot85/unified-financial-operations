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

## Python / Django Concepts

The language- and framework-level mechanisms this app leans on, explained for someone who hasn't necessarily seen them before. This section teaches the *building blocks*; "LLD Concepts" below teaches how this project *composes* them into a pattern.

For each concept:
- **What it is** — plain explanation, not a link to docs.
- **Why this app needs it** — the specific problem it solves here, not a generic feature list.
- **A minor example** — small enough to read in a few seconds, illustrating the mechanism in isolation (not the app's actual code).

> Keep this to genuinely load-bearing concepts — mechanisms this app's design would fall apart without. Skip anything a working Django developer already takes for granted (e.g. don't explain what a `ForeignKey` is; do explain something like descriptors, metaclasses, lazy evaluation, signal timing, or a less-common ORM behavior if the app depends on it).

## LLD Concepts

The design *patterns* this app follows — how the Python/Django mechanisms above get composed into this project's conventions. This is where cross-app conventions (swappable FK targets, `app_settings.py`, `checks.py` + `missing_attrs`, single-concrete-table over MTI, etc.) get explained in the context of *this* app's use of them.

For each pattern:
- **The pattern**, named.
- **Why this app follows it** (vs. an alternative it could have used instead).
- **A minor example** of the shape it takes here.

## Anti-patterns

Concrete things that look reasonable but are wrong for this app, and why. This is the section most worth writing carefully — a good anti-pattern example saves a future contributor (including future-you) from rediscovering a mistake the hard way.

Format per anti-pattern:
- **What it looks like** — the tempting-but-wrong approach, described precisely enough to recognize in a PR.
- **Why it's wrong** — the specific failure mode (not just "it's bad practice").
- **What to do instead** — pointer to the correct pattern above.

## How

Implementation details a developer needs before touching this code. Prose first; code only where prose genuinely can't carry the point (e.g. a signature that's easier to read than to describe).

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
└── README.md               # this file
```

Adjust to actual structure — remove files that don't exist, add ones that do.

## Miscellaneous

- Testing notes (fixtures, factories, anything non-obvious about the test setup).
- TODOs / planned follow-ups (e.g. Protocol classes, deferred refactors).
- Changelog of major revisions to this doc.
