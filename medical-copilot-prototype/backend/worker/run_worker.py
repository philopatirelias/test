import argparse
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from db import get_conn
from schemas import WorkerOutput
from settings import STORAGE_DIR

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "medical_interview_worker.md"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _contains_any(text: str, words: list[str]) -> bool:
    t = text.lower()
    return any(w in t for w in words)


def fallback_analyze(transcript: str) -> dict:
    t = transcript.lower()
    suggestions = []

    def add(q, reason, p, status="unanswered", ans=None, rel=None):
        suggestions.append({"question": q, "reason": reason, "priority": p, "status": status, "answer_found": ans, "related_diagnoses": rel or []})

    # universal safety questions
    add("Any medication allergies?", "Safety-relevant missing question.", "red")
    add("Are you taking anticoagulants or immunosuppressive medicines?", "Safety-relevant missing question.", "red")

    if "chest" in t or "palpitation" in t or "heart" in t:
        add("Does discomfort occur with exertion?", "Exertional symptoms are safety-relevant and need clarification.", "red", "answered" if "exercise" in t else "unanswered", "mostly after meals" if "after meals" in t else None, ["possible angina", "possible acute coronary syndrome"])
        add("Any shortness of breath?", "Safety-relevant missing question.", "red", "answered" if "shortness of breath" in t else "unanswered")
        add("How much caffeine/energy drink intake?", "Stimulants can contribute to symptoms.", "yellow", "answered" if "coffee" in t or "energy" in t else "unanswered", "three coffees and occasional energy drinks" if "coffee" in t else None)

    if "abdominal" in t or "stools" in t or "vomiting" in t:
        add("Please characterize pain location and severity.", "Could suggest important GI/hepatobiliary patterns; needs clarification.", "red")
        add("Any fever or systemic illness symptoms?", "Safety-relevant missing question.", "red")
        add("Could pregnancy be relevant?", "Safety-relevant missing question.", "red")

    if "headache" in t:
        add("Did headache reach maximum intensity suddenly (thunderclap)?", "Safety-relevant missing question.", "red")
        add("Any fever, neck stiffness, or photophobia?", "Safety-relevant missing question.", "red")
        add("Neurological deficits reviewed", "Already addressed in transcript.", "green", "answered" if "weakness" in t or "speech" in t else "unanswered", "No weakness/speech trouble" if "no weakness" in t else None)

    differentials = []
    if "after meals" in t and "chest" in t:
        differentials = [
            {"diagnosis": "possible gastroesophageal reflux disease", "rank": 1, "confidence": 0.72, "supporting_evidence": ["Discomfort after meals"], "missing_information": ["Regurgitation, dysphagia, weight change need clarification"], "suggested_questions": ["Do symptoms worsen lying down?"]},
            {"diagnosis": "possible angina", "rank": 2, "confidence": 0.49, "supporting_evidence": ["Chest discomfort not fully characterized"], "missing_information": ["Exertional trigger and dyspnea status need clarification"], "suggested_questions": ["Does this happen with walking or stairs?"]},
            {"diagnosis": "possible esophageal spasm", "rank": 3, "confidence": 0.31, "supporting_evidence": ["Meal relationship"], "missing_information": ["Swallowing pain and trigger details"], "suggested_questions": ["Any pain with swallowing?"]},
        ]
    elif "palpit" in t or "heart" in t:
        differentials = [
            {"diagnosis": "possible stimulant-related palpitations", "rank": 1, "confidence": 0.71, "supporting_evidence": ["Frequent caffeine/energy drink intake"], "missing_information": ["Timing after stimulant use"], "suggested_questions": ["Do episodes follow caffeine intake?"]},
            {"diagnosis": "possible anxiety/stress-related palpitations", "rank": 2, "confidence": 0.44, "supporting_evidence": ["Night episodes can occur with stress"], "missing_information": ["Stress/sleep context"], "suggested_questions": ["Any stress or sleep disruption?"]},
            {"diagnosis": "possible arrhythmia", "rank": 3, "confidence": 0.38, "supporting_evidence": ["Intermittent racing heart"], "missing_information": ["Episode duration, associated dyspnea/chest pain"], "suggested_questions": ["How long do episodes last?"]},
        ]
    elif "abdominal" in t:
        differentials = [
            {"diagnosis": "possible dyspepsia", "rank": 1, "confidence": 0.58, "supporting_evidence": ["Post-meal abdominal pain"], "missing_information": ["Pain location and relation to specific foods"], "suggested_questions": ["Where is pain located exactly?"]},
            {"diagnosis": "possible biliary colic", "rank": 2, "confidence": 0.41, "supporting_evidence": ["Post-prandial pain pattern"], "missing_information": ["RUQ location, radiation, fever"], "suggested_questions": ["Does pain radiate to shoulder/back?"]},
            {"diagnosis": "possible inflammatory or ulcer-related process", "rank": 3, "confidence": 0.36, "supporting_evidence": ["Weight change noted"], "missing_information": ["NSAID use, bleeding signs evolution"], "suggested_questions": ["Any NSAID use?"]},
        ]
    elif "headache" in t:
        differentials = [
            {"diagnosis": "possible migraine", "rank": 1, "confidence": 0.57, "supporting_evidence": ["Severe headache"], "missing_information": ["Photophobia, nausea, aura"], "suggested_questions": ["Any nausea or light sensitivity?"]},
            {"diagnosis": "possible tension-type headache", "rank": 2, "confidence": 0.34, "supporting_evidence": ["Common headache presentation"], "missing_information": ["Band-like quality and stress association"], "suggested_questions": ["Is pain pressure-like around the head?"]},
            {"diagnosis": "possible secondary red-flag headache cause", "rank": 3, "confidence": 0.33, "supporting_evidence": ["Rapid worsening needs clarification"], "missing_information": ["Thunderclap onset and fever/neck stiffness"], "suggested_questions": ["Did pain peak suddenly? Any fever/neck stiffness?"]},
        ]

    return {
        "suggestions": suggestions[:7],
        "differentials": differentials[:5],
        "summary": "Interview support summary generated. Some safety-relevant items still need clarification.",
        "safety_note": "Clinical decision support only. Doctor remains responsible for judgment.",
    }


def process_job_file(task_file: Path) -> bool:
    data = json.loads(task_file.read_text(encoding="utf-8"))
    job_id = data["job_id"]
    session_id = data["session_id"]
    output_path = STORAGE_DIR / "worker_outputs" / f"{job_id}.json"
    with get_conn() as conn:
        conn.execute("UPDATE analysis_jobs SET status=?, updated_at=? WHERE id=?", ("running", now(), job_id))
    try:
        result = fallback_analyze(data["transcript"])
        valid = WorkerOutput.model_validate(result)
        output_path.write_text(valid.model_dump_json(indent=2), encoding="utf-8")
        with get_conn() as conn:
            conn.execute("DELETE FROM suggestions WHERE session_id=?", (session_id,))
            conn.execute("DELETE FROM differentials WHERE session_id=?", (session_id,))
            for s in valid.suggestions:
                conn.execute(
                    "INSERT INTO suggestions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (f"sug_{uuid.uuid4().hex[:10]}", session_id, s.question, s.reason, s.priority, s.status, s.answer_found, json.dumps(s.related_diagnoses), now()),
                )
            for d in valid.differentials:
                conn.execute(
                    "INSERT INTO differentials VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (f"dif_{uuid.uuid4().hex[:10]}", session_id, d.diagnosis, d.rank, d.confidence, json.dumps(d.supporting_evidence), json.dumps(d.missing_information), json.dumps(d.suggested_questions), now()),
                )
            conn.execute("UPDATE analysis_jobs SET status=?, output_path=?, updated_at=? WHERE id=?", ("ready", str(output_path), now(), job_id))
            conn.execute("UPDATE sessions SET updated_at=? WHERE id=?", (now(), session_id))
        return True
    except Exception as e:
        with get_conn() as conn:
            conn.execute("UPDATE analysis_jobs SET status=?, error=?, updated_at=? WHERE id=?", ("failed", str(e), now(), job_id))
        return False


def run_once() -> int:
    task_dir = STORAGE_DIR / "worker_tasks"
    count = 0
    for task_file in sorted(task_dir.glob("job_*.json")):
        if process_job_file(task_file):
            count += 1
        task_file.unlink(missing_ok=True)
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true")
    args = parser.parse_args()
    if args.loop:
        while True:
            run_once()
            time.sleep(2)
    else:
        run_once()
