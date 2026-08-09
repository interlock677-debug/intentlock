# IntentLock

Enterprise-grade dynamic proof-of-intent authorization gateway for AI agents.

## Architecture

IntentLock follows **Clean Architecture** with four layers:

```
app/
├── domain/           # Entities, value objects, repository contracts, domain rules
├── application/      # Use cases, DTOs, port interfaces
├── infrastructure/   # SQLAlchemy, JWT, bcrypt, settings adapters
└── presentation/     # FastAPI routes, middleware, dependency injection
```

## Quick Start

### Prerequisites

- Python 3.11
- Docker & Docker Compose (optional, for containerized deployment)

### Local Development

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -e ".[dev]"

# Configure environment
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux
# Edit .env and set JWT_SECRET_KEY to a secure random value (min 32 chars)

# Run the API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs (when `DEBUG=true`): http://localhost:8000/docs

### Docker

```bash
copy .env.example .env
# Set JWT_SECRET_KEY in .env
docker compose up --build
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Liveness probe |
| POST | `/api/v1/auth/register` | Register a new user |
| POST | `/api/v1/auth/login` | Authenticate and receive JWT |
| GET | `/api/v1/auth/me` | Get current user (Bearer token required) |

## Security Features

- **JWT authentication** with configurable expiry and HS256 signing
- **Bcrypt password hashing** with configurable work factor
- **Strong password policy** enforced at the DTO layer
- **Input validation** via Pydantic v2 schemas
- **Security headers** middleware (X-Frame-Options, nosniff, etc.)
- **Strict typing** enforced by MyPy in strict mode
- **Static analysis** via Ruff linting and Bandit security scanning

## Development Commands

```bash
# Run tests with coverage
pytest

# Lint and format
ruff check app tests
ruff format app tests

# Type check
mypy app

# Security scan
bandit -r app

# Pre-commit hooks
pre-commit run --all-files
```

## Live Demo

Before running the demo, start the API locally:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then run:

```bash
python demo_agent_defense.py
```

This script shows:

- a legitimate intent being approved and executed
- a destructive SQL request blocked by IntentLock
- an overlimit transfer blocked by IntentLock

Audit logs are written to `logs/audit_trail.jsonl`.

## License

Proprietary — All rights reserved.
