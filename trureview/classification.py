"""
Authenticity classification -> FLAGS, not penalties.

Adapted from the Rumate review-classification-v3 dual-model pattern (a gaming-vs-genuine
detector), inverted for hiring with one locked principle:

  THE AUTHENTICITY LAYER NEVER SUBTRACTS FROM THE SCORE.

It only (a) declines to add credit for unsubstantiated claims — already enforced by
CriterionScore requiring an evidence ref — and (b) raises flags for the human. Two tiers
are the only ones that touch the number:

  * contradicted -> the scorer already scores the artifact, not the claim.
  * fabricated   -> near-total mismatch + JD-shaped: fabricated claims earn no genuine
                    credit, and the recommendation flips to an integrity hold.

`fabricated` is a deliberately HIGH bar and requires BOTH independent reviewer passes to
agree (a fairness control): one stale or missing role never triggers it. Every other flag
favours recall — surfaced if either pass raises it.

Consent boundary intact: corroboration cross-checks only the candidate's OWN provided
sources (resume vs the LinkedIn/portfolio/site links they submitted). No discovery path.

Dual review: two independent passes with opposing stances (skeptical vs charitable) over
one model. Swapping the second pass to a genuinely different model (e.g. Qwen) is a
one-call change behind the same `llm.complete_json` interface — the reconciliation does
not change.
"""

from __future__ import annotations

from .enrichment import fetch_provided
from .llm import load_prompt, get_qwen_llm, AnthropicLLM
from .schemas import Application, ClassificationOutcome, EvidenceBundle, Flag

TIERS = [
    "genuine", "tailored", "contradicted", "derivative",
    "unsubstantiated", "authorship_unclear", "uncertain", "fabricated",
]
SCORE_TOUCHING = {"contradicted", "fabricated"}

# Concise JD (KPMG AI Builder, Senior Consultant) — the reference the classifier checks
# resume language against for JD-mirroring / title-amendment signals.
KPMG_AI_BUILDER_JD = """KPMG AI Builder (Senior Consultant). Build, test, and harden
agents, plugins, skills, and tools using the firm's approved stack. Own the full build
lifecycle: prototype in the AI Lab, productionize through Internal Transformation, and
maintain post-deployment. Work with production systems, design evaluations, and handle
integrations with enterprise platforms and data sources. Contribute reusable skills,
components, and tools back into the shared stack so each build starts further ahead.
Think in workflows, not just models — human-AI handoffs, decision boundaries, appropriate
autonomy. Treat risk, governance, ethics, and trust as core design constraints, not
afterthoughts. Comfortable operating in ambiguity; make reasonable assumptions, build
quickly, test, learn, and iterate."""


def _num(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _source_digest(application: Application) -> str:
    parts = [f"RESUME (candidate-written):\n{application.resume_text}"]
    for link in application.provided_links:
        content = fetch_provided(link, application)  # consent-bounded; raises on non-provided
        parts.append(f"PROVIDED [{link.kind}] {link.label} ({link.url}):\n{content}")
    return "\n\n".join(parts)


def _classify_pass(stance: str, sources: str, llm) -> dict:
    system = load_prompt("classify.md")
    user = (
        f"#TASK:classify\nREVIEWER STANCE: {stance}\n\n"
        f"JOB DESCRIPTION:\n{KPMG_AI_BUILDER_JD}\n\n"
        f"CANDIDATE MATERIALS (resume + the candidate's own provided links):\n{sources}\n\n"
        f"Estimate corroboration_pct and list flags per the tiers. "
        f"Remember: flags only, never a penalty; `fabricated` needs BOTH near-total "
        f"mismatch AND a JD-shaped resume."
    )
    return llm.complete_json(system=f"#TASK:classify\n{system}", user=user) or {}


def _reconcile(a: dict, b: dict) -> ClassificationOutcome:
    flags_a = a.get("flags") or []
    flags_b = b.get("flags") or []

    pa, pb = _num(a.get("corroboration_pct")), _num(b.get("corroboration_pct"))
    if pa is not None and pb is not None:
        corro = round((pa + pb) / 2, 1)
    else:
        corro = pa if pa is not None else pb

    # fabricated requires BOTH reviewers to reach it independently (the fairness bar).
    both_fabricated = (
        any(f.get("tier") == "fabricated" for f in flags_a)
        and any(f.get("tier") == "fabricated" for f in flags_b)
    )

    out: list[Flag] = []
    seen: set[tuple[str, str]] = set()
    for f in [*flags_a, *flags_b]:
        tier = f.get("tier", "uncertain")
        if tier not in TIERS:
            tier = "uncertain"
        claim = (f.get("claim") or "").strip()
        why = (f.get("why") or "").strip()
        # Downgrade a unilateral 'fabricated' — one reviewer alone never clears the bar.
        if tier == "fabricated" and not both_fabricated:
            tier = "uncertain"
            why = "Single-reviewer mismatch only; does not meet the near-total, JD-shaped fabrication bar. " + why
        key = (tier, claim.lower()[:80])
        if key in seen:
            continue
        seen.add(key)
        out.append(Flag(
            tier=tier,
            claim=claim,
            why=why,
            what_to_verify=(f.get("what_to_verify") or "").strip(),
            affects_score=tier in SCORE_TOUCHING,
        ))

    return ClassificationOutcome(flags=out, corroboration_pct=corro, integrity_hold=both_fabricated)


def classify_candidate(application: Application, bundle: EvidenceBundle, llm) -> ClassificationOutcome:
    """Run dual-model classification: haiku (skeptical) vs Qwen-turbo (charitable).

    Two opposing-stance passes over the candidate's own materials, reconciled.

    `bundle` is accepted for interface symmetry with the rest of the pipeline (and so a
    future version can cross-check extracted evidence ids); the corroboration check here
    reads the consented sources directly.
    """
    sources = _source_digest(application)
    try:
        llm_b = get_qwen_llm()
    except Exception:
        llm_b = llm  # fallback if Qwen unavailable
    a = _classify_pass(
        "skeptical — default to doubt on authenticity; demand corroboration before crediting a claim",
        sources, AnthropicLLM(model="claude-sonnet-4-6"),
    )
    b = _classify_pass(
        "charitable — give the benefit of the doubt where the experience plausibly tracks across sources",
        sources, llm_b,
    )
    return _reconcile(a, b)
