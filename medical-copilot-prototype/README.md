# Clinical Interview Copilot (medical-copilot-prototype)

Prototype-only local MVP for clinician interview completeness support.

## Safety
- Prototype only. Clinical interview support, not diagnosis.
- Do not enter patient-identifying information.
- Doctor remains responsible for judgment.

## Stack
- Frontend: Next.js (App Router, TypeScript)
- Backend: FastAPI + SQLite
- Local worker queue: file-based JSON tasks
- Audio: browser MediaRecorder + FFmpeg conversion
- STT: Whisper abstraction with mock default

## Quick start

### 1) Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
uvicorn main:app --reload --port 8000
```

### 2) Worker (optional separate process)
```bash
cd backend
source .venv/bin/activate
python -m worker.run_worker --loop
```

### 3) Frontend
```bash
cd frontend
npm install
cp ../.env.example .env.local
npm run dev
```
Open http://localhost:3000

## Demo mode (no microphone/Whisper required)
1. Create a session in UI.
2. Click **Load Fixture Demo Transcript**.
3. Pick a fixture transcript and submit.
4. Suggestions/differentials update via polling.

## Environment variables
See `.env.example`.

## Tests
```bash
cd backend
source .venv/bin/activate
pytest -q
```

## Known limitations
- Rule-based fallback analyzer, not model-grade reasoning.
- Basic keyword retrieval; no embeddings/vector DB.
- Audio conversion depends on local `ffmpeg` availability.
- In-memory polling UX; no websockets.

## Next step
Replace fallback analyzer with a controlled LLM call behind strict output validation and safety filters while preserving last-valid-state behavior.
