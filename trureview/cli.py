"""CLI entry point.

    python -m trureview.cli --candidate data/candidates/candidate_b_polished_shallow.json
    python -m trureview.cli --candidate data/candidates/candidate_a_strong.json --offline
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import OUTPUTS_DIR
from .enrichment import load_application
from .llm import get_llm
from .pipeline import run_application
from .report import render_markdown
from .rubric import weight_check


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="TruReview — AI Builder candidate evaluator")
    p.add_argument("--candidate", required=True, help="path to candidate JSON")
    p.add_argument("--offline", action="store_true", help="use StubLLM (no tokens, wiring check)")
    p.add_argument("--model", default=None, help="override TRUREVIEW_MODEL")
    p.add_argument("--max-followups", type=int, default=5)
    args = p.parse_args(argv)

    if abs(weight_check() - 1.0) > 1e-6:
        print(f"WARNING: rubric weights sum to {weight_check()}, not 1.0", file=sys.stderr)

    application = load_application(args.candidate)
    llm = get_llm(offline=args.offline, model=args.model)
    report = run_application(application, llm, max_followups=args.max_followups)

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    md = render_markdown(report)
    (OUTPUTS_DIR / f"{report.candidate_id}.md").write_text(md, encoding="utf-8")
    (OUTPUTS_DIR / f"{report.candidate_id}.json").write_text(
        report.model_dump_json(indent=2), encoding="utf-8"
    )

    print(md)
    print(f"\n[written] {OUTPUTS_DIR / (report.candidate_id + '.md')}")
    print(f"[written] {OUTPUTS_DIR / (report.candidate_id + '.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
