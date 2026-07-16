# ADR-<NNNN>: <Decision Title>

> Location: `documentation/technical-architecture/architecture-decision-records/NNNN-<slug>.md` <br/>
> Status: `Proposed | Accepted | Superseded by ADR-XXXX | Deprecated` <br/>
> Date: <date> <br/>
> Deciders: <name(s)> <br/>
> Affected app(s): [<links to app READMEs that must follow this decision>] <br/>

---

## What

The decision itself, stated plainly in 1-3 sentences. Someone skimming just this section should know exactly what was decided, with no ambiguity.

> e.g. "Cross-app FK targets are never hardcoded. Each app exposes swappable model references via `app_settings.py`, overridable per-project via `project_settings.<APP>_APP_SETTINGS`."

## Why

- The problem or recurring pain this decision addresses.
- Forces at play (constraints, requirements, prior incidents) that made a decision necessary.
- Why this needed to be decided *once, centrally* rather than left to each app to figure out independently — this is what separates an ADR from a normal LLD note.

## How

- **The rule, precisely:** the pattern/convention to follow, spelled out so it's directly actionable — not just the principle, but how to apply it (naming conventions, required files, code shape).
- **Alternatives considered:** other options weighed and why they were rejected.
- **Consequences:** what this makes easier, what it makes harder, any tradeoffs accepted knowingly.
- **Example:** a short, concrete before/after or code snippet showing the pattern applied correctly.

## Directory Structure

Where this pattern shows up structurally, if applicable (e.g. a file every app must have):

```
backend/apps/<any_app>/
├── app_settings.py     # required by this ADR
└── checks.py            # required by this ADR
```

Omit this section if the decision isn't structural.

## Miscellaneous

- Migration/adoption notes if this changes an existing pattern (which apps still need to migrate).
- Related ADRs this supersedes, extends, or conflicts with.
- Open questions not yet resolved by this decision.