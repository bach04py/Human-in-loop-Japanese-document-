# Human-in-the-Loop Japanese Document Processing

This repository contains the week 1 base environment for a Human-in-the-Loop Multi-Agent Japanese Document Processing System.

See the full project plan and schedule in the docs: [PROJECT_PLAN.md](docs/PROJECT_PLAN.md)

Week 1 leader deliverables covered here:

- FastAPI backend base with typed API contracts
- Docker Compose environment for backend and Postgres
- Initial OCR, extraction, validation, correction-memory, and orchestration stubs
- Architecture and API documentation for module integration

## Quick Start

Encoding note: source files and documentation are UTF-8 because the project includes Japanese OCR text and Vietnamese planning notes. If PowerShell shows mojibake, set the console to UTF-8 with `chcp 65001` or use an editor that honors `.editorconfig`.

1. Create local environment settings:

```bash
cp .env.example .env
```

2. Create and activate a Python virtual environment.

Windows PowerShell:

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
cd ..
```

macOS/Linux:

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cd ..
```

Use Python 3.11 for this project. The dependency versions in `backend/requirements.txt` are pinned for FastAPI with Pydantic 2 to avoid version conflicts.

3. Run the backend locally:

```bash
cd backend
uvicorn app.main:app --reload
```

4. Or start the backend and database with Docker:

```bash
docker compose up --build
```

5. Open the API docs:

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
- `docs/WEEK1_TEAM_HANDOFF.md`: week 1 task files for every team member
