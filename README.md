# FastAPI Authentication API

A production-ready authentication backend built with **FastAPI**, **PostgreSQL**, **Redis**, and **Docker**. Clean architecture, fully async, and ready for real-world deployment.

---

## Features

| Feature | Implementation |
|---|---|
| Registration | Email + password, hashed with bcrypt |
| Login | JWT access token + opaque refresh token |
| Token refresh | Rotation — old token revoked on use |
| Logout | Access token blacklisted in Redis |
| Email verification | Time-limited UUID token |
| Forgot / Reset password | Time-limited UUID token + forced re-login |
| Role-based access | `user` / `admin` enforced via `Depends()` |
| Rate limiting | `slowapi` with per-IP limits |
| Token revocation | Redis blacklist keyed by JWT `jti` |
| Structured logging | JSON formatter, per-request ID header |
| Health check | `/api/v1/health` — app + Redis status |
| API versioning | All routes under `/api/v1` |
| Pagination | Reusable `PaginationParams` dependency |

---

## Tech Stack

- **Python 3.12** · **FastAPI 0.115** · **SQLAlchemy 2.0** (async) · **asyncpg**
- **Alembic** migrations · **Redis** (asyncio) · **passlib + bcrypt**
- **python-jose** (JWT) · **slowapi** (rate limiting) · **Pydantic v2**
- **pytest + httpx** (async integration tests) · **Docker + Docker Compose**

---

## Project Structure

```
authentication/
├── app/
│   ├── api/v1/
│   │   ├── router.py              # Aggregates all v1 routes
│   │   └── endpoints/
│   │       ├── auth.py            # /auth/* routes
│   │       ├── users.py           # /users/* routes
│   │       └── health.py          # /health
│   ├── core/
│   │   ├── config.py              # pydantic-settings (.env loader)
│   │   ├── security.py            # JWT + bcrypt helpers
│   │   ├── logging.py             # JSON structured logging
│   │   ├── exceptions.py          # Custom exception hierarchy
│   │   └── exception_handlers.py  # Global FastAPI handlers
│   ├── db/
│   │   ├── base.py                # DeclarativeBase + TimestampMixin
│   │   ├── session.py             # Async engine + sessionmaker
│   │   └── init_db.py             # create_all (dev only)
│   ├── models/                    # SQLAlchemy ORM models
│   ├── schemas/                   # Pydantic request/response schemas
│   ├── repositories/              # Async data-access layer
│   ├── services/                  # Business logic
│   ├── middleware/                # RequestLoggingMiddleware
│   ├── dependencies/              # get_db, get_current_user, require_admin
│   └── utils/
│       └── pagination.py          # PaginationParams dependency
├── tests/
│   ├── conftest.py                # SQLite test DB + mocked Redis/email
│   ├── test_auth.py
│   └── test_users.py
├── alembic/                       # Migration scripts
├── main.py                        # App factory + middleware wiring
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── alembic.ini
└── .env.example
```

---

## Quick Start (Docker)

```bash
# 1. Copy and configure environment variables
cp .env.example .env
#    Edit .env — at minimum set SECRET_KEY

# 2. Build and start all services (api + postgres + redis)
docker compose up --build

# 3. Apply database migrations
docker compose exec api alembic upgrade head

# 4. Open interactive API docs
# http://localhost:8000/docs
```

---

## Local Development

### Prerequisites

- Python 3.12+
- PostgreSQL 14+
- Redis 7+

### Setup

```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate      # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env: DATABASE_URL, REDIS_URL, SECRET_KEY

# Run migrations
alembic upgrade head

# Start dev server with auto-reload
uvicorn main:app --reload
```

---

## Running Tests

Tests use **SQLite** (no PostgreSQL required) and mock Redis / email — zero external services needed.

```bash
pytest

# With coverage report
pytest --cov=app --cov-report=term-missing

# Verbose
pytest -v
```

---

## API Endpoints

All routes are prefixed with `/api/v1`.

### Authentication

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | — | Create a new account |
| POST | `/auth/login` | — | Get access + refresh tokens |
| POST | `/auth/refresh` | — | Rotate tokens |
| POST | `/auth/logout` | Bearer | Invalidate session |
| POST | `/auth/forgot-password` | — | Request reset email |
| POST | `/auth/reset-password` | — | Set new password via token |
| POST | `/auth/verify-email` | — | Confirm email via token |

### Users

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/users/me` | Bearer | Get own profile |
| PATCH | `/users/me` | Bearer | Update own profile |
| GET | `/users` | Admin | List all users (paginated) |
| DELETE | `/users/{id}` | Admin | Delete any user |

### Health

| Method | Path | Description |
|---|---|---|
| GET | `/health` | App + Redis health status |

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | **required** | JWT signing key — min 32 chars |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |
| `DATABASE_URL` | **required** | `postgresql+asyncpg://...` |
| `REDIS_URL` | **required** | `redis://...` |
| `ALLOWED_ORIGINS` | `["http://localhost:3000"]` | CORS origins (JSON list) |
| `SMTP_HOST` | `smtp.gmail.com` | Email server host |
| `SMTP_PORT` | `587` | Email server port |
| `SMTP_USER` | *(empty)* | SMTP username |
| `SMTP_PASSWORD` | *(empty)* | SMTP password |
| `EMAILS_FROM_EMAIL` | `noreply@example.com` | Sender address |
| `RATE_LIMIT_PER_MINUTE` | `60` | Max requests per IP per minute |

Generate a secure key: `openssl rand -hex 32`

---

## Database Migrations

```bash
# Auto-generate a migration from model changes
alembic revision --autogenerate -m "add user table"

# Apply all pending migrations
alembic upgrade head

# Roll back one step
alembic downgrade -1

# Show current revision
alembic current
```

---

## Architecture

### Request Lifecycle

```
Client
  └─ CORS Middleware
       └─ Rate Limiter (slowapi)
            └─ Request Logger (JSON, request-id header)
                 └─ Router (/api/v1/...)
                      └─ Dependencies (get_db, get_current_user)
                           └─ Route handler  (validate → call service → return schema)
                                └─ Service   (business logic, no SQL)
                                     └─ Repository  (all SQL lives here)
                                          └─ PostgreSQL / Redis
```

### Security Design

- **Access tokens** are short-lived JWTs. Each carries a unique `jti` so individual tokens can be revoked by writing the `jti` to Redis with TTL = remaining lifetime.
- **Refresh tokens** are opaque UUIDs stored in PostgreSQL. Every use rotates them — the old token is marked `revoked=True` and a new one is issued. Reuse is detected and rejected.
- **Password reset / email verification** tokens are single-use UUIDs. After use, the `used` flag is set and further attempts are rejected.
- **Passwords** are never stored or logged in plaintext — only the bcrypt hash is persisted.

---

<!-- ## Production Checklist

- [ ] Set `SECRET_KEY` to 32+ random chars (`openssl rand -hex 32`)
- [ ] Set `DEBUG=false` and `ENVIRONMENT=production`
- [ ] Configure SMTP credentials for email delivery
- [ ] Set `ALLOWED_ORIGINS` to your actual frontend domain(s)
- [ ] Run `alembic upgrade head` before starting containers
- [ ] Place a TLS-terminating reverse proxy (nginx / Caddy) in front of the API
- [ ] Set Docker resource limits
- [ ] Configure log aggregation (Loki, Datadog, etc.) -->
