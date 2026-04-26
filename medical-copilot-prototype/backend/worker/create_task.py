import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from db import get_conn
from retrieval.search_docs import search_relevant_snippets
from settings import STORAGE_DIR


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_analysis_task(session_id: str, consult_type: str, transcript: str) -> str:
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    task_path = STORAGE_DIR / "worker_tasks" / f"{job_id}.json"
    snippets = search_relevant_snippets(consult_type, transcript)
    payload = {
        "job_id": job_id,
        "session_id": session_id,
        "consult_type": consult_type,
        "transcript": transcript,
        "retrieved_context": snippets,
    }
    task_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO analysis_jobs (id, session_id, status, task_path, output_path, error, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (job_id, session_id, "queued", str(task_path), "", "", now(), now()),
        )
    return job_id
