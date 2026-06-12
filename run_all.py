"""run_all.py — TruReview leaderboard reader.

Reads outputs/leaderboard.json and prints a ranked leaderboard.
With --candidate CAND-X, prints that candidate's full report.

Usage:
    python3 run_all.py
    python3 run_all.py --candidate CAND-B
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

OUTPUTS_DIR = Path(__file__).resolve().parent / "outputs"
LEADERBOARD_PATH = OUTPUTS_DIR / "leaderboard.json"


def load_leaderboard() -> dict:
    return json.loads(LEADERBOARD_PATH.read_text())


def format_leaderboard_text(lb: dict) -> str:
    lines = ["TruReview Leaderboard", "=" * 40]
    for i, c in enumerate(lb["candidates"], 1):
        lines.append(
            f"#{i} {c['candidate_id']} — {c['display_name']}\n"
            f"    Score: {c['composite_score']}\n"
            f"    {c['recommendation']}"
        )
    lines.append(f"\n{lb['disclaimer']}")
    return "\n".join(lines)


def format_candidate_text(c: dict) -> str:
    lines = [
        f"=== {c['candidate_id']} — {c['display_name']} ===",
        f"Composite Score: {c['composite_score']}",
        f"Recommendation: {c['recommendation']}",
        "",
        "Scores:",
    ]
    for k, v in c["scores"].items():
        lines.append(f"  {k}: {v}/5")
    lines += ["", "Top Follow-ups:"]
    for i, q in enumerate(c["top_followups"], 1):
        lines.append(f"  {i}. {q}")
    return "\n".join(lines)


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--candidate", default=None, help="e.g. CAND-B")
    args = p.parse_args(argv)

    lb = load_leaderboard()

    if args.candidate:
        cid = args.candidate.upper()
        if not cid.startswith("CAND-"):
            cid = "CAND-" + cid
        match = next((c for c in lb["candidates"] if c["candidate_id"] == cid), None)
        if not match:
            print(f"Candidate {cid} not found.", file=sys.stderr)
            return 1
        print(format_candidate_text(match))
    else:
        print(format_leaderboard_text(lb))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
