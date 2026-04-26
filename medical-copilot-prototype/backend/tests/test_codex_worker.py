import json
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

import main
from db import get_conn, init_db
from settings import STORAGE_DIR
from worker.codex_runner import extract_json_object, run_codex_job


def _now():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def test_extract_json_object_variants():
    direct = '{"a": 1}'
    wrapped = 'text before\n{"b": 2}\ntext after'
    assert extract_json_object(direct) == {"a": 1}
    assert extract_json_object(wrapped) == {"b": 2}


def test_extract_json_object_raises_without_json():
    try:
        extract_json_object("no json here")
        assert False, "expected failure"
    except Exception:
        assert True


def test_demo_transcript_enqueue_only_in_codex_cli(monkeypatch):
    init_db()
    calls = []

    def fake_run_once():
        calls.append("called")
        return 0

    monkeypatch.setattr(main, "run_once", fake_run_once)
    monkeypatch.setattr(main.settings, "worker_mode", "codex_cli")

    c = TestClient(main.app)
    s = c.post("/sessions", json={"consult_type": "internal_medicine"}).json()["session_id"]
    r = c.post(f"/sessions/{s}/demo-transcript", json={"text": "Patient reports headache"})
    assert r.status_code == 200
    assert r.json()["status"] == "accepted"
    assert calls == []


def test_run_codex_job_invalid_output_preserves_last_valid(monkeypatch):
    init_db()
    session_id = f"sess_{uuid.uuid4().hex[:10]}"
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    task_path = STORAGE_DIR / "worker_tasks" / f"{job_id}.json"
    output_path = STORAGE_DIR / "worker_outputs" / f"{job_id}.json"

    with get_conn() as conn:
        conn.execute("INSERT INTO sessions VALUES (?, ?, ?, ?, ?)", (session_id, "internal_medicine", _now(), _now(), "active"))
        conn.execute(
            "INSERT INTO suggestions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (f"sug_{uuid.uuid4().hex[:10]}", session_id, "Existing question", "Existing reason", "yellow", "unanswered", None, "[]", _now()),
        )
        conn.execute(
            "INSERT INTO differentials VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (f"dif_{uuid.uuid4().hex[:10]}", session_id, "possible diagnosis", 1, 0.2, "[]", "[]", "[]", _now()),
        )
        conn.execute(
            "INSERT INTO analysis_jobs (id, session_id, status, task_path, output_path, error, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (job_id, session_id, "queued", str(task_path), "", "", _now(), _now()),
        )

    task_path.write_text(
        json.dumps(
            {
                "job_id": job_id,
                "session_id": session_id,
                "consult_type": "internal_medicine",
                "transcript": "Patient has dizziness",
                "retrieved_context": [],
            }
        ),
        encoding="utf-8",
    )

    class Dummy:
        stdout = "not-json"

    def fake_run(*args, **kwargs):
        return Dummy()

    monkeypatch.setattr("worker.codex_runner.subprocess.run", fake_run)

    failed = False
    try:
        run_codex_job(str(task_path), str(output_path))
    except Exception:
        failed = True
    assert failed

    with get_conn() as conn:
        job = conn.execute("SELECT status FROM analysis_jobs WHERE id=?", (job_id,)).fetchone()
        sugs = conn.execute("SELECT question FROM suggestions WHERE session_id=?", (session_id,)).fetchall()
        diffs = conn.execute("SELECT diagnosis FROM differentials WHERE session_id=?", (session_id,)).fetchall()

    assert job["status"] == "failed"
    assert any(r["question"] == "Existing question" for r in sugs)
    assert any(r["diagnosis"] == "possible diagnosis" for r in diffs)

    task_path.unlink(missing_ok=True)
    Path(output_path).unlink(missing_ok=True)


def test_demo_transcript_runs_inline_in_fallback(monkeypatch):
    init_db()
    calls = []

    def fake_run_once():
        calls.append("called")
        return 0

    monkeypatch.setattr(main, "run_once", fake_run_once)
    monkeypatch.setattr(main.settings, "worker_mode", "fallback")

    c = TestClient(main.app)
    s = c.post("/sessions", json={"consult_type": "internal_medicine"}).json()["session_id"]
    r = c.post(f"/sessions/{s}/demo-transcript", json={"text": "Patient reports headache"})
    assert r.status_code == 200
    assert calls == ["called"]
