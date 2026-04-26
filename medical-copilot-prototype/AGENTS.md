# AGENTS.md

## Project purpose
Clinical Interview Copilot is a **local-first internal prototype** that helps doctors run more complete medical interviews by tracking answered questions, suggesting follow-ups, and presenting cautious *possible differential hypotheses*.

## Medical safety boundaries
- Prototype only; **not diagnosis**.
- Doctor remains responsible for clinical judgment.
- Never request patient identifiers (name, DOB, address, phone, email, national ID, insurance number).
- Never provide treatment recommendations, prescribing logic, triage decisions, or diagnostic certainty.
- UI and outputs must use cautious language (e.g., "possible", "needs clarification", "could suggest").

## Run / test / lint commands
### Backend
- Install: `cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- Run API: `uvicorn main:app --reload --port 8000`
- Run tests: `pytest -q`

### Frontend
- Install: `cd frontend && npm install`
- Run: `npm run dev`
- Lint: `npm run lint`
- Build: `npm run build`

## Directory map
- `frontend/`: Next.js UI.
- `backend/`: FastAPI API, SQLite persistence, worker queue, safety checks.
- `documents/`: consult-type markdown interview templates.
- `fixtures/`: demo transcript fixtures.
- `storage/`: local artifacts (audio/transcripts/tasks/outputs).

## Coding conventions
- Keep implementation simple, local-first, strongly typed where practical.
- Prefer deterministic behavior for MVP fallback logic.
- Use structured JSON logs for backend events.
- Keep API handlers responsive; avoid long blocking operations.

## Required implementation rules
- All UI copy must frame differentials as **hypotheses**, not confirmed diagnoses.
- No patient identifiers should be requested anywhere.
- Worker output **must be validated** before storage.
- Delete-session must remove all related local artifacts.
- Web request paths must not wait indefinitely on AI analysis.
