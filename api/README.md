# TheAutisticNIDS API

> Phase 1 — FastAPI backend for the Network Intrusion Detection System.

## Project Structure

```
api/
├── app/
│   ├── core/           # Settings & configuration
│   │   └── config.py
│   ├── db/             # Database layer
│   │   ├── base.py     # SQLAlchemy DeclarativeBase
│   │   ├── models.py   # ORM models (flows, predictions, alerts, …)
│   │   └── session.py  # Async engine & session factory
│   ├── models/         # Pydantic schemas
│   │   └── schemas.py
│   ├── routes/         # API endpoints
│   │   ├── health.py   # GET /health
│   │   ├── predict.py  # POST /predict
│   │   ├── alerts.py   # GET /alerts, GET /alerts/{id}
│   │   └── models.py   # GET /models
│   ├── services/       # Business logic
│   │   └── prediction.py
│   └── main.py         # FastAPI app factory
├── migrations/         # Alembic migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── tests/              # pytest test suite
│   ├── conftest.py     # Fixtures (in-memory SQLite)
│   ├── test_health.py
│   ├── test_predict.py
│   ├── test_alerts.py
│   └── test_models.py
├── alembic.ini
├── Dockerfile
├── pyproject.toml
└── README.md           # ← you are here
```

## Endpoints

| Method | Path              | Description                        |
|--------|-------------------|------------------------------------|
| GET    | `/health`         | Health check + DB connectivity     |
| POST   | `/predict`        | Run inference on flow features     |
| GET    | `/alerts`         | Paginated, filterable alert list   |
| GET    | `/alerts/{id}`    | Single alert detail                |
| GET    | `/models`         | List registered model versions     |

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL (or use SQLite for local dev/tests)

### Install

From the project root directory, synchronize all workspace dependencies (which sets up a unified `.venv/` virtual environment):
```bash
uv sync
```

### Configure

Copy the `.env.example` from the project root and adjust:

```bash
cp ../.env.example .env
# Edit DATABASE_URL, MLFLOW_TRACKING_URI, etc.
```

### Run Migrations

```bash
alembic upgrade head
```

### Start the Server

From the project root directory, launch the API server:
```bash
uv run --package nids-api uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at: [http://localhost:8000/docs](http://localhost:8000/docs)

### Run Tests

Execute the API test suite using the `uv` environment runner from the project root:
```bash
uv run pytest api/tests/ -v --cov
```

Tests use an in-memory SQLite database — no external services needed.

### Docker

```bash
docker build -t nids-api .
docker run -p 8000:8000 --env-file .env nids-api
```

## Design Decisions

- **Async everywhere** — SQLAlchemy 2.0 async + asyncpg for non-blocking I/O.
- **Forward-compatible schema** — nullable columns for Phases 2–6 already present.
- **Mock inference** — Phase 1 uses random predictions; swap to MLflow in Phase 2.
- **Dependency injection** — `get_db()` is overridden in tests for SQLite.
- **Pydantic v2** — strict validators, `model_validate()`, `ConfigDict`.
