"""Run the full TruReview pipeline on all candidates in parallel using haiku."""
import subprocess, sys, os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

CANDIDATES_DIR = Path(__file__).parent / "data" / "candidates"
VENV_PYTHON = Path(__file__).parent / ".venv312" / "bin" / "python3"
candidates = sorted(CANDIDATES_DIR.glob("*.json"))

env = os.environ.copy()

def run_one(path):
    result = subprocess.run(
        [str(VENV_PYTHON), "-m", "trureview.cli", "--candidate", str(path), "--model", "claude-sonnet-4-5"],
        cwd=str(Path(__file__).parent),
        capture_output=True, text=True, timeout=180, env=env
    )
    return path.name, result.returncode, result.stdout[-300:], result.stderr[-300:]

print(f"Running {len(candidates)} candidates with claude-haiku-4-5 in parallel...")
with ThreadPoolExecutor(max_workers=4) as ex:
    futures = {ex.submit(run_one, c): c for c in candidates}
    for f in as_completed(futures):
        name, rc, out, err = f.result()
        status = "OK" if rc == 0 else "FAIL"
        print(f"[{status}] {name}")
        if rc != 0:
            print("  STDERR:", err[-200:])
        else:
            # print last written line
            for line in out.splitlines():
                if "[written]" in line:
                    print(" ", line)

print("Done.")
