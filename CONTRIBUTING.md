# Contributing Guidelines

Thank you for your interest in contributing to **TheAutisticNIDS**! This project is a multi-phase, end-to-end network intrusion detection platform built with robust Software Engineering and Machine Learning standards. 

To maintain high code quality, please adhere to the guidelines outlined below.

---

## 📂 Monorepo Architecture Overview

This project is structured as a monorepo with distinct separation of concerns:
- **`ml/`**: Machine Learning pipeline (data cleaning, feature engineering, model training, evaluation).
- **`api/`**: Asynchronous FastAPI backend providing database models, Alembic migrations, and REST endpoints.
- **`web/`**: Next.js 15 App Router frontend leveraging TypeScript and Recharts for data visualization.
- **`Docs/`**: Architectural specs and phased deliverables roadmap.

---

## 🛠️ Local Environment Setup

### Prerequisites
- Docker & Docker Compose
- Python 3.10+ (for ML/API development)
- Node.js 18+ & npm (for Web development)
- Git

### Initializing the Monorepo
1. Clone the repository and navigate to the project directory:
   ```bash
   git clone https://github.com/TheAutisticAPI/Net_Attack_detection.git
   cd Net_Attack_detection
   ```
2. Copy the environment template and configure secrets:
   ```bash
   cp .env.example .env
   ```
3. Spin up the entire platform infrastructure (PostgreSQL, MLflow, API, Next.js) using Docker Compose:
   ```bash
   docker compose up --build
   ```

---

## 🌿 Git Branching Strategy

We follow a structured branching model to keep development histories clean and reviewable:

- **`main`**: Production-ready branch. Must always be stable.
- **`feature/`**: New feature tracks (e.g., `feature/ml-anomaly-layer` or `feature/api-auth`).
- **`bugfix/`**: Remediation of issues in active components (e.g., `bugfix/prevent-inf-nan-split`).
- **`chore/`**: General maintenance, package upgrades, or CI/CD updates.

### Workflow
1. Branch off `main` with a descriptive name: `git checkout -b feature/your-feature-name`.
2. Commit in small, logical chunks using **Conventional Commits**.
3. Rebase or merge from `main` frequently to prevent merge conflicts.
4. Open a Pull Request referencing the issue or phase step.

---

## 📝 Commit Message Format

We strictly enforce **Conventional Commits** formats. This allows automatic changelog generation and maintains a clear revision log.

Format: `<type>(<scope>): <short summary>` (followed by optional body/footer).

### Commit Types
* **`feat`**: A new user-facing feature (e.g., `feat(ml): add Isolation Forest anomaly detection`)
* **`fix`**: A bug fix (e.g., `fix(api): handle empty dataset queries in alerts`)
* **`docs`**: Changes to documentation only (e.g., `docs: update deployment guidelines`)
* **`style`**: Layout, formatting, white-space, semi-colons (no logic modifications)
* **`refactor`**: Re-writing code without changing external behaviors (e.g., `refactor(web): extract chart wrapper`)
* **`perf`**: Changes aimed at improving database or inference speed (e.g., `perf(ml): optimize log-transform loop`)
* **`test`**: Creating, modifying, or repairing unit/integration tests
* **`chore`**: Infrastructure adjustments, dependencies, config files (e.g., `chore: update docker-compose config`)

### Examples
- `feat(ml): integrate SHAP TreeExplainer for flow predictions`
- `fix(web): prevent crash when Recharts receives zero-value series`
- `test(api): add healthcheck integration tests`

---

## 💻 Code Standards & Quality Guidelines

### 🐍 Python Guidelines (`ml/` & `api/`)
- **Environment Management**: We use [uv](https://github.com/astral-sh/uv) to manage workspace environments and lock files.
  - **Setup**: Run `uv sync` at the monorepo root to automatically bootstrap the unified workspace environment (`.venv/` in the root).
  - **Adding Dependencies**: Use the workspace package targets:
    - Add to ML pipeline: `uv add --package nids-ml <package>`
    - Add to API backend: `uv add --package nids-api <package>`
    - Add development dependencies: `uv add --package nids-api --dev <package>`
  - **Synchronization**: If dependencies in any member `pyproject.toml` are modified, sync the environment by running `uv sync` from anywhere in the project.
- **Coding Style**: Conform to [PEP 8](https://peps.python.org/pep-0008/).
- **Formatting**: We use [Black](https://github.com/psf/black) with default settings (line length 88) for deterministic code formatting.
- **Type Annotations**: Apply strong static type hints to all function signatures (`typing` module / native types).
- **Asynchronous Operations**: Backend endpoints in `api/` must leverage `async`/`await` paradigms for all database and remote resource interactions.
- **Unit Testing**: 
  - Every new module must include companion tests under the `tests/` directory.
  - Run ML tests using: `uv run pytest ml/tests/`
  - Run API tests using: `uv run pytest api/tests/`

### ⚛️ Next.js & TypeScript Guidelines (`web/`)
- **Coding Style**: ESLint configured with the default Next.js configuration.
- **Formatting**: Format frontend assets with Prettier: `npx prettier --write .`
- **TypeScript**:
  - Avoid using the `any` escape hatch; declare explicit interfaces and types for properties and API responses.
  - Synchronize Pydantic API response shapes in `api/` with typescript interfaces in `web/src/lib/types.ts`.
- **Styling**: Standard CSS Modules or modern global custom properties. No utility class pollution; use predefined semantic CSS selectors.

---

## 🗃️ Database Migrations

- Any modifications to the database schema (`api/app/db/models.py`) must be accompanied by an Alembic migration.
- **Generating a migration**:
  ```bash
  docker compose exec api alembic revision --autogenerate -m "describe changes"
  ```
- **Reviewing migrations**: Check the auto-generated migration script in `api/migrations/versions/` to verify it maps accurately to relational requirements.

---

## 🤝 Pull Request (PR) Checklist

Before submitting a Pull Request, verify:
1. All unit tests pass across both tracks (`ml` and `api`).
2. Build commands finish without warnings (`npm run build` or local docker assemblies).
3. The project compiles on multi-architecture structures (both x86_64 and ARM64).
4. Any newly created endpoints are fully documented in OpenAPI definitions via FastAPI routers.
5. `CHANGELOG.md` is updated in the "Unreleased" section if making user-facing additions or security corrections.
