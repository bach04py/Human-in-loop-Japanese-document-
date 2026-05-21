# Human-in-the-Loop Japanese Document Processing

This repository contains the week 1 base environment for a Human-in-the-Loop Multi-Agent Japanese Document Processing System.

See the full project plan and schedule in the docs: [PROJECT_PLAN.md](docs/PROJECT_PLAN.md)

Week 1 leader deliverables covered here:

- FastAPI backend base with typed API contracts
- Docker Compose environment for backend and Postgres
- Initial OCR, extraction, validation, correction-memory, and orchestration stubs
- Architecture and API documentation for module integration

## Quick Start

1. Create local environment settings:

```bash
cp .env.example .env
```

2. Start the backend and database:

```bash
docker compose up --build
```

3. Open the API docs:

```text
http://localhost:8000/docs
```

Health check:

```text
GET http://localhost:8000/api/v1/healthz
```

## Project Layout

- `backend/app/api`: FastAPI routes and module API surface
- `backend/app/schemas`: shared request/response contracts
- `backend/app/services`: week 1 service stubs for agents and orchestration
- `docs/API_CONTRACT.md`: endpoint contract for frontend, OCR, extraction, and feedback modules
- `docs/WEEK1_LEADER_DELIVERABLES.md`: checklist against the team leader plan
