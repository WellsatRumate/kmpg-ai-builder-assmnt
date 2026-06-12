"""
Weighted composite scoring. Each criterion is scored 0-5 against its JD anchor and
behavioural descriptors, MUST cite evidence_ids, and contributes weight * score.

Composite is normalised to 0-100. The recommendation is an advisory band, never a
gate. Nothing here auto-rejects.
"""

from __future__ import annotations

from .llm import load_prompt
from .rubric import CRITERIA, ORIGINALITY_CLUSTER
from .schemas import CriterionScore, EvidenceBundle


def _evidence_digest(bundle: EvidenceBundle) -> str:
    lines = []
    for e in bundle.items:
        lines.append(f"[{e.evidence_id}] ({e.source_label}) {e.claim_or_signal} :: {e.relevance}")
    return "\n".join(lines) if lines else "(no evidence items)"


def score_candidate(bundle: EvidenceBundle, llm) -> list[CriterionScore]:
    system = load_prompt("score.md")
    digest = _evidence_digest(bundle)
    valid_ids = {e.evidence_id for e in bundle.items}

    criteria_block = "\n".join(
        f"- id={c['id']} name={c['name']} jd_anchor={c['jd_anchor']} "
        f"strong={c['what_strong']} weak={c['what_weak']}"
        for c in CRITERIA
    )

    user = (
        f"#TASK:score\n"
        f"Score ALL criteria below in ONE response. Be terse — rationale max 15 words each.\n\n"
        f"CRITERIA:\n{criteria_block}\n\n"
        f"EVIDENCE:\n{digest}\n\n"
        f"Return a JSON array, one object per criterion, same order:\n"
        f"[{{\"id\": \"...\", \"score_0_5\": 0-5, \"evidence_refs\": [...], \"rationale\": \"...\"}}]\n"
        f"Cite only evidence_ids that exist above. Score 0 if evidence is thin."
    )
    results = llm.complete_json(system=f"#TASK:score\n{system}", user=user, max_tokens=4096)
    if isinstance(results, dict):
        results = results.get("scores", list(results.values()))

    results_by_id = {r["id"]: r for r in results if isinstance(r, dict) and "id" in r}

    scores: list[CriterionScore] = []
    for crit in CRITERIA:
        result = results_by_id.get(crit["id"], {})
        refs = [r for r in result.get("evidence_refs", []) if r in valid_ids]
        raw_score = float(result.get("score_0_5", 0))
        if raw_score > 0 and not refs:
            raw_score = 0.0
            rationale = (
                "No verifiable evidence cited for this criterion; scored 0 rather than "
                "inferring. " + result.get("rationale", "")
            )
        else:
            rationale = result.get("rationale", "")
        scores.append(
            CriterionScore(
                criterion_id=crit["id"],
                criterion_name=crit["name"],
                weight=crit["weight"],
                score_0_5=raw_score,
                evidence_refs=refs,
                rationale=rationale,
            )
        )
    return scores


def composite_0_100(scores: list[CriterionScore]) -> float:
    weighted = sum(s.weight * (s.score_0_5 / 5.0) for s in scores)
    return round(weighted * 100, 1)


# Recommendation when the authenticity pass reaches the high-bar `fabricated` case.
# Note: still advisory and human-owned — surfaced, never an auto-reject.
INTEGRITY_HOLD_RECOMMENDATION = (
    "Integrity hold — do NOT advance on this submission as-is. Near-total mismatch "
    "between the stated experience and the candidate's own provided history "
    "(LinkedIn/portfolio), in a resume shaped to this JD. Verify directly with the "
    "candidate before any further step. Advisory only: confirm, do not auto-reject."
)


def recommendation_band(score: float) -> str:
    # Advisory only. Bands describe interviewer next-action, not a decision.
    if score >= 70:
        return "Advance — strong signal. Use follow-ups to confirm depth."
    if score >= 50:
        return "Advance with reservations — follow-ups target the gaps before deciding."
    if score >= 30:
        return "Borderline — evidence is thin; follow-ups are decisive here."
    return "Insufficient evidence to advance on current submission — invite more artifacts."


# --- Originality cluster -> role translation ------------------------------------
# originality + innovation + ingenuity, scored from evidence like everything else,
# then read together and translated into what they predict for THIS role. This is
# the answer to "if a candidate scores on those, what does it mean for an AI Builder?"

def originality_cluster_0_5(scores: list[CriterionScore]) -> float:
    """Weight-blended mean (0-5) of the originality cluster criteria."""
    members = [s for s in scores if s.criterion_id in ORIGINALITY_CLUSTER]
    if not members:
        return 0.0
    wsum = sum(s.weight for s in members) or 1.0
    return round(sum(s.weight * s.score_0_5 for s in members) / wsum, 2)


def originality_signal(cluster_0_5: float) -> str:
    if cluster_0_5 >= 4.0:
        return "HIGH"
    if cluster_0_5 >= 2.5:
        return "MODERATE"
    return "LOW"


def originality_role_translation(signal: str) -> str:
    """What an originality signal predicts for the AI Builder role. Advisory, and
    deliberately cross-referenced to builder-evidence so novelty alone is never the
    headline — invention that shipped is the signal, not novelty for its own sake."""
    if signal == "HIGH":
        return (
            "Rare, high-leverage signal. In a shared builder pool 'deployed against the "
            "highest-leverage builds', this is the candidate who finds the non-obvious wedge "
            "in an ambiguous problem and invents reusable primitives that compound across every "
            "downstream build (JD: 'contribute reusable skills so each build starts further ahead'). "
            "Confirm it is grounded — read alongside Builder Evidence: reward invention that "
            "shipped and was used, not cleverness on a slide. If both are high, prioritise."
        )
    if signal == "MODERATE":
        return (
            "Some inventive spark above competent execution. Likely a reliable builder who "
            "occasionally finds a better path than the default. Use the ingenuity follow-ups to "
            "test whether the originality is repeatable or a one-off, and whether it survives "
            "contact with enterprise constraints."
        )
    return (
        "Competent execution of known patterns; little divergence from the default approach. "
        "Not disqualifying — much of the role is reliable delivery — but this is unlikely to be "
        "the builder who finds the wedge others miss. Read against Builder Evidence: a strong "
        "builder with low originality is a solid journeyman; a weak builder with low originality "
        "is a pass."
    )
