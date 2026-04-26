import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from db import get_conn, init_db
from schemas import (
    CreateSessionRequest,
    CreateSessionResponse,
    DemoTranscriptRequest,
    HealthResponse,
    SessionStateResponse,
    DifferentialOut,
    SuggestionOut,
)
from settings import STORAGE_DIR, settings
from audio.convert import convert_to_wav
from stt.whisper_client import WhisperClient
from worker.create_task import create_analysis_task
from worker.run_worker import run_once

app = FastAPI(title="Clinical Interview Copilot API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_event(event: str, endpoint: str, session_id: str | None = None, latency_ms: int | None = None, error: str | None = None) -> None:
    payload = {
        "correlation_id": uuid.uuid4().hex[:12],
        "session_id_hash": hashlib.sha256((session_id or "none").encode()).hexdigest()[:12],
        "endpoint": endpoint,
        "event": event,
    }
    if latency_ms is not None:
        payload["latency_ms"] = latency_ms
    if error:
        payload["error_type"] = error
    print(json.dumps(payload))


def fetch_transcript(session_id: str) -> str:
    with get_conn() as conn:
        rows = conn.execute("SELECT text FROM transcript_chunks WHERE session_id=? ORDER BY chunk_index", (session_id,)).fetchall()
    return "\n".join(r["text"] for r in rows)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/sessions", response_model=CreateSessionResponse)
def create_session(req: CreateSessionRequest) -> CreateSessionResponse:
    sid = f"sess_{uuid.uuid4().hex[:10]}"
    with get_conn() as conn:
        conn.execute("INSERT INTO sessions VALUES (?, ?, ?, ?, ?)", (sid, req.consult_type, now(), now(), "created"))
    return CreateSessionResponse(session_id=sid, status="created")


def _insert_chunk(session_id: str, text: str, audio_path: str | None, idempotency_key: str | None = None) -> int:
    with get_conn() as conn:
        if idempotency_key:
            dup = conn.execute(
                "SELECT chunk_index FROM transcript_chunks WHERE session_id=? AND idempotency_key=?",
                (session_id, idempotency_key),
            ).fetchone()
            if dup:
                return int(dup["chunk_index"])
        row = conn.execute("SELECT COALESCE(MAX(chunk_index), -1) AS m FROM transcript_chunks WHERE session_id=?", (session_id,)).fetchone()
        idx = int(row["m"]) + 1
        conn.execute(
            "INSERT INTO transcript_chunks VALUES (?, ?, ?, ?, ?, ?, ?)",
            (f"chk_{uuid.uuid4().hex[:10]}", session_id, idx, text, audio_path, now(), idempotency_key),
        )
        conn.execute("UPDATE sessions SET updated_at=?, status=? WHERE id=?", (now(), "active", session_id))
        return idx


@app.post("/sessions/{session_id}/demo-transcript")
def add_demo_transcript(session_id: str, req: DemoTranscriptRequest):
    with get_conn() as conn:
        sess = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    _insert_chunk(session_id, req.text, None, None)
    transcript = fetch_transcript(session_id)
    job_id = create_analysis_task(session_id, sess["consult_type"], transcript)
    if settings.worker_mode == "fallback":
        run_once()
    return {"status": "accepted", "job_id": job_id}


@app.post("/sessions/{session_id}/audio")
async def upload_audio_chunk(session_id: str, file: UploadFile = File(...), idempotency_key: str = Form(default="")):
    start = time.time()
    with get_conn() as conn:
        sess = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    base = STORAGE_DIR / "audio" / session_id
    raw_dir = base / "raw"
    wav_dir = base / "wav"
    raw_dir.mkdir(parents=True, exist_ok=True)
    wav_dir.mkdir(parents=True, exist_ok=True)
    stamp = int(time.time() * 1000)
    raw_path = raw_dir / f"{stamp}_{file.filename or 'chunk.webm'}"
    raw_path.write_bytes(await file.read())

    wav_path = wav_dir / f"{stamp}.wav"
    ok, convert_detail, convert_ms = convert_to_wav(raw_path, wav_path)
    log_event("ffmpeg_convert", f"/sessions/{session_id}/audio", session_id, convert_ms, None if ok else "ffmpeg_error")
    if not ok:
        return {"status": "retryable_error", "message": "Audio conversion failed safely", "detail": convert_detail[-200:]}

    whisper = WhisperClient()
    t0 = time.time()
    transcript_text = whisper.transcribe(wav_path)
    transcribe_ms = int((time.time() - t0) * 1000)
    log_event("transcription", f"/sessions/{session_id}/audio", session_id, transcribe_ms)

    idx = _insert_chunk(session_id, transcript_text, str(wav_path), idempotency_key or None)
    full_transcript = fetch_transcript(session_id)
    job_id = create_analysis_task(session_id, sess["consult_type"], full_transcript)
    if settings.worker_mode == "fallback":
        run_once()

    total_ms = int((time.time() - start) * 1000)
    log_event("audio_upload", f"/sessions/{session_id}/audio", session_id, total_ms)

    return {"status": "accepted", "chunk_index": idx, "transcript_chunk": transcript_text, "job_id": job_id}


@app.get("/sessions/{session_id}/state", response_model=SessionStateResponse)
def get_state(session_id: str):
    with get_conn() as conn:
        sess = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found")
        sug_rows = conn.execute("SELECT * FROM suggestions WHERE session_id=? ORDER BY updated_at DESC", (session_id,)).fetchall()
        diff_rows = conn.execute("SELECT * FROM differentials WHERE session_id=? ORDER BY rank ASC", (session_id,)).fetchall()
        job = conn.execute("SELECT status FROM analysis_jobs WHERE session_id=? ORDER BY updated_at DESC LIMIT 1", (session_id,)).fetchone()

    transcript = fetch_transcript(session_id)
    suggestions = [
        SuggestionOut(
            question=r["question"], reason=r["reason"], priority=r["priority"], status=r["status"],
            answer_found=r["answer_found"], related_diagnoses=json.loads(r["related_diagnoses"] or "[]")
        ) for r in sug_rows
    ]
    differentials = [
        DifferentialOut(
            diagnosis=r["diagnosis"], rank=r["rank"], confidence=r["confidence"],
            supporting_evidence=json.loads(r["supporting_evidence"] or "[]"),
            missing_information=json.loads(r["missing_information"] or "[]"),
            suggested_questions=json.loads(r["suggested_questions"] or "[]"),
        ) for r in diff_rows
    ]
    return SessionStateResponse(
        session_id=session_id,
        consult_type=sess["consult_type"],
        status=sess["status"],
        transcript=transcript,
        suggestions=suggestions,
        differentials=differentials,
        analysis_status=job["status"] if job else "pending",
        safety_note="Clinical decision support only. Doctor remains responsible for judgment.",
    )


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    paths = [
        STORAGE_DIR / "audio" / session_id,
        STORAGE_DIR / "transcripts" / f"{session_id}.txt",
    ]
    with get_conn() as conn:
        task_rows = conn.execute("SELECT task_path, output_path FROM analysis_jobs WHERE session_id=?", (session_id,)).fetchall()
        for tr in task_rows:
            if tr["task_path"]:
                paths.append(Path(tr["task_path"]))
            if tr["output_path"]:
                paths.append(Path(tr["output_path"]))
        conn.execute("DELETE FROM transcript_chunks WHERE session_id=?", (session_id,))
        conn.execute("DELETE FROM suggestions WHERE session_id=?", (session_id,))
        conn.execute("DELETE FROM differentials WHERE session_id=?", (session_id,))
        conn.execute("DELETE FROM analysis_jobs WHERE session_id=?", (session_id,))
        conn.execute("DELETE FROM sessions WHERE id=?", (session_id,))

    import shutil
    for p in paths:
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        elif p.exists():
            p.unlink(missing_ok=True)
    return {"status": "deleted", "session_id": session_id}
