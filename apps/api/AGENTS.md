# AGENTS.md — Backend (`apps/api`)

This file applies to all work under `apps/api`. Read it before changing backend code.

## Stack

- Python 3.12, FastAPI, Uvicorn
- SQLAlchemy 2.0 async ORM with `aiosqlite`
- SQLite database at `apps/api/data/app.db` (ignored by git)
- Alembic migrations in `apps/api/migrations/`
- `pyproject.toml` with setuptools; `ruff`, `pytest`, and `httpx` for development

## Setup

Run these commands from `apps/api`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## Commands

Run these commands from `apps/api`:

```powershell
# Development server
.\.venv\Scripts\uvicorn.exe app.main:app --reload

# Lint
.\.venv\Scripts\ruff.exe check app

# Tests
.\.venv\Scripts\pytest.exe

# Apply migrations
.\.venv\Scripts\alembic.exe upgrade head

# Create a migration after changing models
.\.venv\Scripts\alembic.exe revision --autogenerate -m "describe the change"
```

## Architecture

- `app/config.py` — `DATABASE_URL` and path configuration. Override the URL with the
  `DATABASE_URL` environment variable. Never hard-code credentials.
- `app/db.py` — declarative `Base`, async engine, `SessionLocal`, and the `get_db`
  request dependency.
- `app/models.py` — SQLAlchemy ORM models. `Task` is a starter model and may be
  replaced or extended.
- `app/main.py` — FastAPI application and routes. Split routes into routers once the
  API grows beyond a few endpoints.
- `migrations/` — Alembic environment and versioned schema changes. `env.py` uses the
  app's metadata and `DATABASE_URL` so the API and migrations cannot drift.
- `data/` — local SQLite files. Never commit this directory or database files.

## Coding conventions

- Use Python 3.12 type hints on all functions, methods, and module-level variables
  where the type is not obvious.
- Keep the request path async end to end: async routes, `AsyncSession`, and
  `aiosqlite`. Do not introduce a synchronous SQLAlchemy session.
- Inject database sessions with
  `Annotated[AsyncSession, Depends(get_db)]`. Do not create engines or sessions
  inside route handlers.
- Define Pydantic request and response schemas separately from ORM models unless
  there is a clear reason to share them.
- Never create tables with `Base.metadata.create_all()`. All schema changes go
  through Alembic.
- After changing a model, generate and review a migration, then run
  `alembic upgrade head`. Commit the migration with the model change.
- Keep transactions short. Use `await session.commit()` only when the unit of work
  is complete, and `await session.rollback()` on failure where appropriate.
- Read configuration from environment variables. Never commit `.env` files,
  credentials, tokens, or local database files.
- Keep route handlers thin. Put reusable business logic in services or domain
  modules rather than duplicating it in endpoints.

## Comments and docstrings

- Add a module docstring to every Python module that contains logic.
- Add Google-style docstrings to every public class and public function, including
  FastAPI route handlers. Describe behavior, arguments, return values, and raised
  exceptions where they are not obvious.
- Document non-obvious constraints and decisions with comments that explain **why**,
  not **what** the next line does.
- Keep comments and docstrings accurate when behavior changes. Do not leave stale or
  commented-out code behind.
- Do not use comments to compensate for unclear names; rename or simplify first.

Example:

```python
async def get_task(db: AsyncSession, task_id: int) -> Task:
    """Return a task by ID.

    Args:
        db: Active database session.
        task_id: Primary key of the task.

    Raises:
        HTTPException: If the task does not exist.
    """
```

## Testing

- Place tests under `apps/api/tests/`, mirroring the `app/` structure.
- Tests must be independent and must not use `data/app.db`. Point `DATABASE_URL` at a
  temporary SQLite file or an in-memory database and apply migrations or create the
  schema explicitly in test setup.
- Cover success paths, validation failures, and database error paths.
- Run `ruff check app` and `pytest` before committing.

## Git commits

Use this exact two-message structure:

```powershell
git commit -m "{type}: {summary}" -m "{body}"
```

Rules:

- `{type}` is one of `feat`, `fix`, `docs`, `refactor`, `test`, `perf`, `build`, `ci`,
  or `chore`.
- `{summary}` is imperative, lowercase, at most 72 characters, and has no trailing
  period. Example: `feat: add task creation endpoint`.
- The second `-m` is the body. Explain what changed and why, wrapped at 72
  characters. Use the body for context, trade-offs, and migration notes.
- Reference issues in the body (`Refs #123`, `Closes #123`).
- Mark breaking changes with a `BREAKING CHANGE:` paragraph in the body.
- Keep each commit focused on one logical change. Do not mix refactoring, formatting,
  and behavior changes.
- Run lint and tests before committing.
- Never commit `.venv/`, `data/`, `*.db`, caches, or secrets.

Example:

```powershell
git commit -m "feat: add task creation endpoint" -m "Add POST /tasks so the frontend can create automation tasks. Validate input with a Pydantic schema and persist it through the async session. Refs #42."
```

## Branching and pull requests

- Branch from `main` using `{type}/{short-description}`, for example
  `feat/tasks-api` or `fix/session-rollback`.
- Keep pull requests small and focused on one concern. Self-review the diff before
  requesting review.
- Rebase or merge `main` into your branch to resolve conflicts; do not force-push
  `main` or other shared branches.
- Ensure linting and tests pass before marking a PR ready for review.
- Use the PR title format `{type}: {summary}`, matching the commit convention.
- Use squash merge so the PR title and body become the commit on `main`.

Use this PR structure in the same order for every PR:

```markdown
## Summary

What this PR does and why.

## Changes

- Key change one
- Key change two

## Testing

- [ ] `ruff check app`
- [ ] `pytest`
- [ ] `alembic upgrade head` on a clean database
- [ ] Manual verification (endpoint, payload, or scenario)

## Related Issues

Closes #123

## Checklist

- [ ] Follows the commit and PR conventions
- [ ] Tests added or updated
- [ ] Migration added for model changes
- [ ] Documentation updated when behavior changes
- [ ] No secrets, credentials, local databases, or generated files committed
```
