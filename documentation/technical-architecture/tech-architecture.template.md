# HLD: <Feature / System Name>

> Location: `documentation/technical-architecture/<feature-name>.md` <br/>
> Status: `Draft | Proposed | Approved | Superseded` <br/>
> Owner: <name> <br/>
> Last updated: <date> <br/>
> Related BRD: [<link to business-requirement-documents doc>] <br/>
> Related ADRs: [<links>] <br/>
> Implementing app(s): [<links to app READMEs>] <br/>


## What

One paragraph describing the feature/system as a black box — what it does, its scope boundary, and what it explicitly does *not* cover. A reader with zero context should be oriented after this section.

## Why

- Problem being solved / business driver.
- What happens if we don't build this.
- Link to BRD for full product rationale — don't duplicate it here, just enough context to justify the technical approach.

## How

High-level design. This is the meat of the document — describe the shape of the solution, not the line-by-line implementation (that belongs in the app-level LLD).

- **Components involved:** which apps/services participate and their responsibility.
- **Data flow:** how data/requests move through the system (diagram if non-trivial).
- **Key models / contracts:** the cross-app entities and interfaces this design introduces or touches, at a conceptual level.
- **Integration points:** external systems, APIs, feature flags, or other in-repo systems this touches.
- **Alternatives considered:** other approaches and why they were rejected (brief — full tradeoff analysis can live in an ADR if it's a significant decision).

## Directory Structure

Which parts of the repo this feature spans, at a high level (apps/modules, not files):

```
backend/apps/<app_a>/     # role in this feature
backend/apps/<app_b>/     # role in this feature
frontend/src/modules/...  # role in this feature
```

## Miscellaneous

- Open questions / known unknowns.
- Rollout plan, feature flag name(s) if applicable.
- Non-functional considerations (perf, security, multi-tenancy implications).
- Changelog of major revisions to this doc.