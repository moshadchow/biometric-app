# Repository Guidelines

## Project Structure & Module Organization

This repository is split into two main applications:

- `frontend/`: React + TypeScript customer/admin UI built with Vite.
- `frontend/src/components/`: UI components for onboarding, admin dashboards, face capture, OCR, and signatures.
- `frontend/src/api/`, `services/`, `hooks/`, `types/`, and `constants/`: API clients, business logic, shared hooks, and TypeScript contracts.
- `frontend/src/__tests__/`: Vitest specs.
- `frontend/public/`: static assets, including face-api model files.
- `backend/`: FastAPI backend with API routers, CRUD logic, SQLModel models, Celery tasks, Alembic migrations, and tests.
- `backend/tests/`: Python unit tests for onboarding, compliance, and risk assessment behavior.

## Build, Test, and Development Commands

Run frontend commands from `frontend/`:

- `npm run dev`: start the Vite dev server.
- `npm run build`: run TypeScript checks and create the production bundle.
- `npm run preview`: serve the production build locally.
- `npm run test`: start Vitest in watch mode.
- `npx vitest run --no-cache`: run frontend tests once.
- `npx tsc --noEmit`: run TypeScript type checks only.

Run backend commands from `backend/`:

- `uvicorn main:app --reload --port 8000`: start the API server.
- `.\venv\Scripts\python.exe -m unittest discover tests`: run backend tests.
- `.\venv\Scripts\alembic.exe heads`: inspect Alembic migration heads.
- `.\venv\Scripts\celery.exe -A worker.celery_app worker -I tasks --pool=solo --loglevel=info`: start Celery on Windows.

## Coding Style & Naming Conventions

Use React function components and TypeScript in the frontend. Prefer `@/` imports for internal frontend modules. Keep formatting consistent with existing files: 2-space indentation, double quotes, and `PascalCase` component names. Hooks use `useCamelCase`; service files use `*.service.ts`.

Backend code uses Python, FastAPI, SQLModel, and Alembic. Keep routers in `backend/api/`, shared logic in `backend/core/`, persistence helpers in `backend/crud/`, and database models in `backend/model/models.py`.

## Testing Guidelines

Frontend tests use Vitest and live under `frontend/src/__tests__/` with `*.test.ts` or `*.test.tsx` names. Backend tests use `unittest` and live under `backend/tests/`. Add focused tests when changing scoring, onboarding state, compliance decisions, OCR, face matching, or signature behavior.

## Commit & Pull Request Guidelines

Commit history favors short, imperative messages such as `ocr-extractor+stepper-shell` or `add backend folder structure`. Keep commits focused. Pull requests should include a brief summary, commands run, linked issues when relevant, and screenshots or recordings for UI changes.

## Security & Configuration Tips

Do not commit secrets, credentials, or generated binaries outside approved static assets. Keep environment-specific values in config files or environment variables. Be careful with auth, session recovery, onboarding eligibility, and risk scoring changes because they affect compliance-sensitive workflows.
