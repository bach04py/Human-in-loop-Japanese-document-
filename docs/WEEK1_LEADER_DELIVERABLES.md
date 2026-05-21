# Week 1 Team Leader Deliverables

Owner: Bach - Team Leader & System Architect

## Scope From Plan

- Research Multi-Agent workflow
- Research Human-in-the-loop systems
- Design system architecture
- Setup FastAPI backend
- Setup Docker environment
- Design API contract between modules

## Completed In This Repo

### Overall Architecture

- Architecture diagram exists in `docs/architecture.mmd`.
- Backend package is split by responsibility:
  - `api`: HTTP contract
  - `schemas`: shared Pydantic models
  - `services`: agent and workflow stubs
  - `core`: environment settings

### FastAPI Backend

- `GET /api/v1/healthz`
- `POST /api/v1/documents`
- `POST /api/v1/ocr`
- `POST /api/v1/extract`
- `POST /api/v1/validate`
- `POST /api/v1/feedback`
- `POST /api/v1/pipeline/run`

### Docker Environment

- `docker-compose.yml` starts:
  - FastAPI backend
  - PostgreSQL 15
  - named upload volume
- `.env.example` documents required environment variables.

### API Contract

- `docs/API_CONTRACT.md` defines the first stable request/response contract for all modules.
- OpenAPI docs are available after startup at `http://localhost:8000/docs`.

## Next Week Handoff

- Replace `OcrService` stub with PaddleOCR Japanese baseline.
- Replace `ExtractionService` stub with LayoutLM/LLM extraction prototype.
- Replace in-memory correction memory with Postgres tables.
- Replace `OrchestratorService` with LangGraph once agent states are defined.
