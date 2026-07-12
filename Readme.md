# Unified Financial Operations Platform (UFOP)

A white labeled, multi tenant financial operations platform. The platform adopts to the unique needs for different organizations. Unlike rigid, single-purpose software, our platform evolves with our clients.

Currently, we are launching the platform to serve our immediate client—an NGO requiring a donation portal with automated tax receipts. However, the underlying architecture is designed to instantly transform into a full-fledged bookkeeping system for Small and Medium Businesses (SMBs) or a personal expense tracker for individual users, all from the same codebase.

**Our mission:** Single source of truth for an organization’s financial lifeblood, _from the moment a payment is initiated, to the final entry in their accounting ledger._

## Tech Stack

<p align="center">
  <img src="documentation/logos/django-logo-negative.png" width="150" height="80" alt="Django Logo" />
  <img src="documentation/logos/drf-logo-dark.png" width="150" height="80" alt="DRF Logo" />
  <img src="documentation/logos/vue-logo.png" width="100" height="80" alt="Vue Logo" />
  <img src="documentation/logos/celery-logo.webp" width="100" height="80" alt="celery logo" />
  <img src="documentation/logos/elephant.png" width="100" height="80" alt="postgres logo" />
  <img src="documentation/logos/docker-mark-ocean-blue.svg" width="100" height="80" alt="docker logo" />
</p>

---

| Component          | Technologies                                                          |
| :----------------- | :-------------------------------------------------------------------- |
| **Backend**        | django (5.2), django-rest-framework, django-tenants, django-constance |
| **Frontend**       | Vue 3 (Composition API), Vite, Vuetify 3, Pinia                       |
| **Worker/Queue**   | Celery, Valkey                                                        |
| **Database**       | PostgreSQL                                                            |
| **Infrastructure** | Docker, Compose, Poetry, Pre-Commit                                   |

## Directory Structure

```
project-root/
|	|- .agents/ 			# Common agentic configs, skills, plugins
|	|- .vscode/				# IDE settings for vscode
|	|- .github/				# Github related settings
|	|- documentation/		# Project wide documentation, architecture and assets
|	|- backend/				# Complete Backend Application
|	|- frontend/			# Complete Frontend Application
|	|- compose/				# Dockerfile(s) and docker-compose configurations
|	|- .gitignore
|	|- .dockerignore
|	|- .env.example
|	|- .pre-commit-config.yaml
```

- **`backend/`**: Contains the complete Django project, including apps, configuration, and management scripts.
- **`frontend/`**: Contains the Vue 3 SPA, including components, assets, and build configuration.
- **`compose/`**: Docker Compose configuration files for various environments.
- **`documentation/`**: Architectural specifications, diagrams, and developer guides.
- **Root Directory**: Houses environment variables (`.env`), CI/CD configurations, repository-wide tools (`Makefile`, `pre-commit`), and project metadata.

### Reason behind the directory structure

This structure is designed to leverage **Docker BuildKit's** context isolation:

- During the backend build, only the `backend/` directory is provided as context.
- During the frontend build, only the `frontend/` directory is provided as context.

This eliminates accidental leakage of irrelevant code (e.g., frontend source in the backend image) and ensures that changes in one domain do not unnecessarily invalidate the build cache of the other.
This also gives us future scope of easily splitting backend from frontend.

## Documentation Hub

The project believes in clearly documenting what is being built or added, general idea is to start from a brainstormed plan and at the end of feature the documentation should be clearly able to describe the feature, mindset behind it and what is solves.
The Documentation should clealy answer: _What_, _Why_ and _How_.<br/>
Each Documentation directory has a dedicated `Readme.md` file that has general overview and also contains index to the rest of the documentation files.<br/>

### Principle

- **HLD (High-Level Design)** — lives centrally in `documentation/`. Product POV, architecture, cross-cutting decisions.
- **LLD (Low-Level Design)** — lives colocated with each app as `README.md` at the app root. Models, implementation details, gotchas.

Every doc should answer **What**, **Why**, and **How**.

```
project-root/
|	|- documentation/
|   |- Readme.md
|   |- technical-architecture/
|   |   |- Readme.md                        # HLD index, links to ADRs + app registry
|   |   |- architecture-decision-records/   # Record for common architectural decisions
|   |       |- 0001-swappable-fk-pattern.md
|	|		|- ...
|   |- logos/
|	|- business-requirement-documents/      # Common agentic configs, skills, plugins
|- backend/
|   |- README.md                            # index of all apps, links to each
|   |- apps/
|       |- crm/README.md                    # LLD: models, swappable settings, checks.py
|       |- notification_app/README.md
|       |- ledger/README.md
|- frontend/
|   |- README.md
|- compose/
|- .vscode/
|- .github/
|- .agents/
```

- [**business-requirement-documents:**](./documentation/business-requirement-documents/Readme.md) Houses all the business related documentation, this gives a product side pov and overview of a feature and its implementation.
- [**technical-architecture:**](./documentation/technical-architecture/Readme.md) Houses all the technical high level design and architecture for a feature or functionality.
- [**Backend LLD Index:**](./backend/Readme.md) Backend general practices, project conventions and Backend LLD Index.
- [**Frontend LLD Index:**](./backend/Readme.md) Frontend general practices and project conventions.
- [**logos:**](./documentation/logos/) Logos used across the repository.

### Rules

1. **Cross-linking is mandatory, not optional.**

- Every app `README.md` must link up to the HLD doc(s)/ADR(s) it implements.
- Every HLD doc must link down to the app README(s) that implement it.
- Without this link, the two layers drift silently.

2. **App registry:** `backend/README.md` (or `technical-architecture/Readme.md`) maintains a table of every app with a one-line purpose and a link to its README — a single place to discover what exists.

3. **ADRs for cross-cutting patterns:** Anything that spans multiple apps (e.g. the swappable-FK pattern, `missing_attrs`/`checks.py` contract convention, "no MTI — concrete inheritance + proxy models only") belongs in `technical-architecture/adr/`, not buried in whichever app's README happened to describe it first. App READMEs reference the ADR instead of re-explaining it.

4. **PR checklist enforcement:** Any PR touching an app's models, contracts, or swappable settings must update that app's `README.md` in the same PR. Colocation only prevents staleness if it's enforced at review time.


## Local Development Setup

### Makefile hierarchy

### Quick Start Local Setup

```bash
make build 		# Builds the entire project image(S)
make run 		# Run (Build Conatiners) from built image(s) attached
```

Seed local data using:

```bash
make setup			# Run all the seeder(s) and get complete local setup
make light-setup	# Only setup tenant(s) and users
```

## User Credentials (Local Development)

The following pre-configured accounts are available for testing:

| Role                         | Username              | Password     | Domain                     |
| :--------------------------- | :-------------------- | :----------- | :------------------------- |
| **Platform Admin**           | `admin@localhost.com` | `qwerty@123` | `localhost:8000`           |
| **Tenant Admin (NGO)**       | `admin@localngo.com`  | `qwerty@123` | `localngo.localhost:8000`  |
| **Tenant Admin (Restraunt)** | `admin@restraunt.com` | `qwerty@123` | `restraunt.localhost:8000` |
| **Client/User (NGO)**        | `client@localngo.com` | `qwerty@123` | `localngo.localhost:8000`  |

_Note: Map these domains to `127.0.0.1` in your `/etc/hosts` file for local testing._
