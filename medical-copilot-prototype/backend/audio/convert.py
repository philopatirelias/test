from pathlib import Path
import subprocess
import time


def convert_to_wav(input_path: Path, output_path: Path) -> tuple[bool, str, int]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    start = time.time()
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-ac",
        "1",
        "-ar",
        "16000",
        str(output_path),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        ok = proc.returncode == 0
        return ok, proc.stderr[-1000:], int((time.time() - start) * 1000)
    except Exception as e:
        return False, str(e), int((time.time() - start) * 1000)
