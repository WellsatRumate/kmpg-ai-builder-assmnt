"""Assemble the Report and render it as markdown for the demo/video."""

from __future__ import annotations

from .schemas import (
    Application, ClassificationOutcome, CriterionScore, Deliberation, EvidenceBundle,
    FollowUp, Report,
)
from .scoring import (
    INTEGRITY_HOLD_RECOMMENDATION,
    composite_0_100,
    originality_cluster_0_5,
    originality_role_translation,
    originality_signal,
    recommendation_band,
)


def build_report(
    application: Application,
    bundle: EvidenceBundle,
    scores: list[CriterionScore],
    deliberation: Deliberation,
    follow_ups: list[FollowUp],
    classification: ClassificationOutcome | None = None,
) -> Report:
    composite = composite_0_100(scores)
    cluster = originality_cluster_0_5(scores)
    signal = originality_signal(cluster)
    classification = classification or ClassificationOutcome()
    # The ONLY place the authenticity layer touches the output: the high-bar `fabricated`
    # case flips the recommendation to an integrity hold. The composite itself is never
    # penalized — fabricated claims simply earned no genuine credit upstream.
    recommendation = (
        INTEGRITY_HOLD_RECOMMENDATION if classification.integrity_hold
        else recommendation_band(composite)
    )
    return Report(
        candidate_id=application.candidate_id,
        display_name=application.display_name,
        composite_score=composite,
        recommendation=recommendation,
        criterion_scores=scores,
        deliberation=deliberation,
        follow_ups=follow_ups,
        originality_cluster_0_5=cluster,
        originality_signal=signal,
        originality_role_translation=originality_role_translation(signal),
        flags=classification.flags,
        corroboration_pct=classification.corroboration_pct,
        integrity_hold=classification.integrity_hold,
        redaction_log=bundle.redaction_log,
    )


def render_markdown(report: Report) -> str:
    L = []
    L.append(f"# TruReview — {report.display_name} ({report.candidate_id})")
    L.append("")
    L.append(f"**Composite (advisory): {report.composite_score}/100**")
    L.append(f"**Recommendation: {report.recommendation}**")
    if report.integrity_hold:
        L.append("")
        L.append("> ⚠️ **INTEGRITY HOLD** — near-total mismatch between the resume and the "
                 "candidate's own provided history, in a JD-shaped resume. Surfaced for human "
                 "verification; this is not an auto-reject.")
    L.append("")
    L.append(f"> {report.disclaimer}")
    L.append("")
    L.append("## Scores (each traced to a JD criterion + evidence)")
    L.append("")
    L.append("| Criterion | Weight | Score | Evidence | Rationale |")
    L.append("|---|---|---|---|---|")
    for s in report.criterion_scores:
        refs = ", ".join(s.evidence_refs) if s.evidence_refs else "—"
        rat = s.rationale.replace("|", "\\|")
        L.append(f"| {s.criterion_name} | {s.weight} | {s.score_0_5}/5 | {refs} | {rat} |")
    L.append("")
    L.append("## Originality, innovation & ingenuity → role translation")
    L.append("")
    L.append(
        f"**Originality signal: {report.originality_signal}** "
        f"(cluster {report.originality_cluster_0_5}/5)"
    )
    cluster_rows = [
        s for s in report.criterion_scores
        if s.criterion_id in ("originality", "innovation", "ingenuity")
    ]
    if cluster_rows:
        parts = ", ".join(f"{s.criterion_name.split(' (')[0]} {s.score_0_5}/5" for s in cluster_rows)
        L.append("")
        L.append(f"_{parts}_")
    L.append("")
    L.append(f"{report.originality_role_translation}")
    L.append("")
    L.append("## Integrity & authenticity flags")
    L.append("")
    L.append(
        "_Flags never penalize the score — they surface concerns for the human. Only "
        "`contradicted` (the artifact is scored, not the claim) and `fabricated` "
        "(integrity hold) touch the output._"
    )
    L.append("")
    if report.corroboration_pct is not None:
        L.append(f"**Corroboration across provided sources: ~{report.corroboration_pct}%**")
        L.append("")
    if report.flags:
        L.append("| Tier | Claim | Why | Verify | Score effect |")
        L.append("|---|---|---|---|---|")
        for fl in report.flags:
            claim = (fl.claim or "—").replace("|", "\\|")
            why = (fl.why or "").replace("|", "\\|")
            ver = (fl.what_to_verify or "").replace("|", "\\|")
            eff = "scored" if fl.affects_score else "flag only"
            L.append(f"| `{fl.tier}` | {claim} | {why} | {ver} | {eff} |")
    else:
        L.append("- No authenticity concerns surfaced.")
    L.append("")
    L.append("## Dual-LLM deliberation")
    L.append("")
    for t in report.deliberation.turns:
        cites = f" _(cites {', '.join(t.cites)})_" if t.cites else ""
        L.append(f"- **{t.persona} / {t.facet}:** {t.argument}{cites}")
    L.append("")
    L.append(f"**Synthesis:** {report.deliberation.synthesis}")
    if report.deliberation.open_questions:
        L.append("")
        L.append("**Open questions:**")
        for q in report.deliberation.open_questions:
            L.append(f"- {q}")
    L.append("")
    L.append("## Targeted follow-ups (serve the human interviewer)")
    L.append("")
    for i, f in enumerate(report.follow_ups, 1):
        L.append(f"**{i}. [{f.gap_type}]** target: _{f.target_claim}_")
        L.append(f"   - Q: {f.question}")
        L.append(f"   - A strong answer shows: {f.what_a_strong_answer_shows}")
        L.append("")
    L.append("## Redaction audit log")
    if report.redaction_log:
        for r in report.redaction_log:
            L.append(f"- {r}")
    else:
        L.append("- No protected-category signals detected in provided evidence.")
    L.append("")
    return "\n".join(L)
