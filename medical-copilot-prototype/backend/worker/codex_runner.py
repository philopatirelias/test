import json
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from db import get_conn
from safety import contains_phi_request
from schemas import WorkerOutput
from settings import STORAGE_DIR, settings

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "medical_interview_worker.md"

MINIMAL_REJECT_PHRASES = [
    "the patient has",
    "definitely",
    "prescribe",
    "start medication",
]
PHI_FIELDS = {"name", "date_of_birth", "dob", "address", "phone", "email", "insurance", "national_id"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def extract_json_object(text: str) -> dict:
    text = text.strip()
    try:
        loaded = json.loads(text)
        if isinstance(loaded, dict):
            return loaded
        raise ValueError("JSON root is not an object")
    except Exception:
        pass

    start = text.find("{")
    if start < 0:
        raise ValueError("No JSON object found")

    depth = 0
    in_string = False
    escape = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start:idx + 1]
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
                raise ValueError("Extracted JSON root is not an object")

    raise ValueError("No valid JSON object could be extracted")


def _contains_forbidden_output(text: str) -> bool:
    lower = text.lower()
    return any(p in lower for p in MINIMAL_REJECT_PHRASES) or contains_phi_request(lower)


def _contains_phi_fields(obj: dict) -> bool:
    serialized = json.dumps(obj, ensure_ascii=False).lower()
    if contains_phi_request(serialized):
        return True
    keys = {k.lower() for k in obj.keys()}
    return not PHI_FIELDS.isdisjoint(keys)


def _build_prompt(task_json: str) -> str:
    rules = PROMPT_PATH.read_text(encoding="utf-8")
    return (
        "You are a clinical interview support assistant for an internal prototype.\n\n"
        "You are NOT diagnosing.\n"
        "You are helping a doctor conduct a more complete interview.\n\n"
        "Read the task JSON below.\n\n"
        "Use the rules from:\n"
        "backend/worker/prompts/medical_interview_worker.md\n\n"
        "Return ONLY valid JSON.\n"
        "No markdown.\n"
        "No explanation.\n"
        "No code blocks.\n\n"
        "Follow these rules strictly:\n"
        "- Suggest 3–7 follow-up questions\n"
        "- Mark answered questions as completed\n"
        "- Use cautious language: possible, could suggest, needs clarification\n"
        "- Do NOT give treatment advice\n"
        "- Do NOT give diagnostic certainty\n"
        "- Do NOT request patient-identifying information\n\n"
        "Output must EXACTLY match the required JSON schema.\n\n"
        "WORKER RULES:\n"
        f"{rules}\n\n"
        "TASK JSON:\n"
        f"{task_json}\n"
    )


def run_codex_job(task_path: str, output_path: str) -> None:
    task_file = Path(task_path)
    out_file = Path(output_path)
    data = json.loads(task_file.read_text(encoding="utf-8"))
    job_id = data["job_id"]
    session_id = data["session_id"]

    print(f"job started: {job_id}")
    with get_conn() as conn:
        conn.execute("UPDATE analysis_jobs SET status=?, updated_at=? WHERE id=?", ("running", now(), job_id))

    try:
        task_json = json.dumps(data, ensure_ascii=False, indent=2)
        prompt = _build_prompt(task_json)
        result = subprocess.run(
            [settings.codex_command],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=settings.codex_timeout_seconds,
            check=False,
        )
        stdout = (result.stdout or "").strip()
        if not stdout:
            raise ValueError("Codex CLI returned empty stdout")

        parsed = extract_json_object(stdout)
        if _contains_forbidden_output(stdout):
            raise ValueError("Forbidden language detected in worker output")
        if _contains_phi_fields(parsed):
            raise ValueError("Forbidden PHI fields detected in worker output")

        valid = WorkerOutput.model_validate(parsed)
        out_file.write_text(valid.model_dump_json(indent=2), encoding="utf-8")

        with get_conn() as conn:
            conn.execute("DELETE FROM suggestions WHERE session_id=?", (session_id,))
            conn.execute("DELETE FROM differentials WHERE session_id=?", (session_id,))
            for s in valid.suggestions:
                conn.execute(
                    "INSERT INTO suggestions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        f"sug_{uuid.uuid4().hex[:10]}",
                        session_id,
                        s.question,
                        s.reason,
                        s.priority,
                        s.status,
                        s.answer_found,
                        json.dumps(s.related_diagnoses),
                        now(),
                    ),
                )
            for d in valid.differentials:
                conn.execute(
                    "INSERT INTO differentials VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        f"dif_{uuid.uuid4().hex[:10]}",
                        session_id,
                        d.diagnosis,
                        d.rank,
                        d.confidence,
                        json.dumps(d.supporting_evidence),
                        json.dumps(d.missing_information),
                        json.dumps(d.suggested_questions),
                        now(),
                    ),
                )
            conn.execute(
                "UPDATE analysis_jobs SET status=?, output_path=?, error=?, updated_at=? WHERE id=?",
                ("ready", str(out_file), "", now(), job_id),
            )
            conn.execute("UPDATE sessions SET updated_at=? WHERE id=?", (now(), session_id))
        print(f"job completed: {job_id}")
    except Exception as exc:
        with get_conn() as conn:
            conn.execute(
                "UPDATE analysis_jobs SET status=?, error=?, updated_at=? WHERE id=?",
                ("failed", str(exc), now(), job_id),
            )
        print(f"job failed: {job_id}")
        raise
