"""End-to-end pipeline: Application -> Report.

    enrich (consent-bounded) -> score (traceable) -> deliberate (dual-LLM)
    -> follow-ups (strategy+draft) -> report (advisory)
"""

from __future__ import annotations

from .classification import classify_candidate
from .deliberation import deliberate
from .enrichment import enrich
from .followups import generate_followups
from .report import build_report
from .schemas import Application, Report
from .scoring import score_candidate


def run_application(application: Application, llm, max_followups: int = 5) -> Report:
    bundle = enrich(application, llm)
    scores = score_candidate(bundle, llm)
    classification = classify_candidate(application, bundle, llm)
    delib = deliberate(bundle, llm)
    follow_ups = generate_followups(bundle, scores, llm, max_questions=max_followups)
    return build_report(application, bundle, scores, delib, follow_ups, classification)
