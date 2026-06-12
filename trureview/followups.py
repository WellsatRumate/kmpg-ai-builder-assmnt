"""
Follow-up generator — the verification layer, and the novel bit.

Two-stage, reusing the BYAMN strategy + draft division of labour:

  * STRATEGY: scans scores, rationales, and the evidence bundle to find the
    highest-leverage GAPS BETWEEN CLAIM AND EVIDENCE. Not "weakest claim" —
    specifically claims with high polish and no supporting artifact, plus
    unverified scope ("led X") and depth probes. This is the direct answer to the
    brief's own line: you can outsource thinking, you cannot outsource understanding.

  * DRAFT: writes a candidate-specific question for each selected gap, plus what a
    strong answer would reveal — so the human interviewer can probe understanding
    rather than re-reading polished prose.

The output serves the interviewer. It is not a score and not a decision.
"""

from __future__ import annotations

from .llm import load_prompt
from .schemas import CriterionScore, EvidenceBundle, FollowUp


def _gap_context(bundle: EvidenceBundle, scores: list[CriterionScore]) -> str:
    ev = "\n".join(f"[{e.evidence_id}] {e.claim_or_signal}" for e in bundle.items) or "(no evidence)"
    sc = "\n".join(
        f"{s.criterion_name}: {s.score_0_5}/5 | refs={s.evidence_refs or 'NONE'} | {s.rationale}"
        for s in scores
    )
    return f"EVIDENCE:\n{ev}\n\nSCORES & RATIONALES:\n{sc}"


def generate_followups(
    bundle: EvidenceBundle, scores: list[CriterionScore], llm, max_questions: int = 5
) -> list[FollowUp]:
    strategy_system = load_prompt("strategy_gaps.md")
    draft_system = load_prompt("draft_questions.md")

    gaps = llm.complete_json(
        system=f"#TASK:gaps\n{strategy_system}",
        user=(
            f"#TASK:gaps\n{_gap_context(bundle, scores)}\n\n"
            f"Identify up to {max_questions} highest-leverage claim-evidence gaps. "
            f"Return JSON: gaps[] with target_claim, gap_type "
            f"(claim_without_evidence|high_polish_low_artifact|unverified_scope|depth_probe)."
        ),
    ).get("gaps", [])

    from concurrent.futures import ThreadPoolExecutor, as_completed

    def draft_one(gap):
        d = llm.complete_json(
            system=f"#TASK:draft\n{draft_system}",
            user=(
                f"#TASK:draft\nTARGET CLAIM: {gap.get('target_claim','')}\n"
                f"GAP TYPE: {gap.get('gap_type','')}\n\n"
                f"Write one specific, non-leading interview question that probes genuine "
                f"understanding of this claim, and what a strong answer reveals. "
                f"Return JSON: question, what_a_strong_answer_shows."
            ),
        )
        return FollowUp(
            target_claim=gap.get("target_claim", ""),
            gap_type=gap.get("gap_type", "depth_probe"),
            question=d.get("question", ""),
            what_a_strong_answer_shows=d.get("what_a_strong_answer_shows", ""),
        )

    selected = gaps[:max_questions]
    followups: list[FollowUp] = [None] * len(selected)
    with ThreadPoolExecutor(max_workers=len(selected) or 1) as ex:
        futures = {ex.submit(draft_one, gap): i for i, gap in enumerate(selected)}
        for f in as_completed(futures):
            followups[futures[f]] = f.result()
    return followups
