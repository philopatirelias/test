import argparse
import json
import time
from pathlib import Path

from settings import STORAGE_DIR
from worker.codex_runner import run_codex_job


def process_one(task_file: Path) -> bool:
    data = json.loads(task_file.read_text(encoding="utf-8"))
    output_path = STORAGE_DIR / "worker_outputs" / f"{data['job_id']}.json"
    try:
        run_codex_job(str(task_file), str(output_path))
        return True
    except Exception:
        return False
    finally:
        task_file.unlink(missing_ok=True)


def run_once(max_jobs: int | None = None) -> int:
    task_dir = STORAGE_DIR / "worker_tasks"
    processed = 0
    for task_file in sorted(task_dir.glob("job_*.json")):
        process_one(task_file)
        processed += 1
        if max_jobs is not None and processed >= max_jobs:
            break
    return processed


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Process one job and exit")
    args = parser.parse_args()

    if args.once:
        run_once(max_jobs=1)
    else:
        while True:
            run_once()
            time.sleep(2)
