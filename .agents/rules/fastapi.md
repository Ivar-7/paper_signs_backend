# FastAPI

## Architecture
- **Application** — `app/main.py`: application creation, router registration, and exception handlers.
- **Features** — `app/modules/<feature>/`: routers, schemas, services, persistence, and tests for one domain.
- **Request Dependencies** — `app/dependencies/`: shared request-scoped dependencies.
- **Runtime Configuration** — `app/config/`: runtime configuration.

## Core Rules
- **Schemas** — Use Pydantic models for JSON request bodies and JSON response bodies.
- **Dependencies** — Use FastAPI dependencies for request-scoped services, authorization, and resources.
- **I/O** — Await network and database I/O; keep CPU-bound work outside the event loop.
- **Boundaries** — Keep route handlers limited to HTTP concerns and service delegation.
- **Errors** — Translate domain errors through centralized exception handlers; never expose tracebacks.
- **Testing** — Test the ASGI application without a network listener through an ASGI test client.

## Project Conventions
- **Persistence** — Use SQLAlchemy and Alembic.
- **Authentication** — Use `fastapi.security` OAuth2 dependencies and PyJWT for JWT encoding and verification.
- **Configuration** — Use `pydantic-settings` and maintain `.env.example`.

## Verification
- **Checks** — Run `ruff check .`, `ruff format --check .`, and `mypy .`; fix failures.