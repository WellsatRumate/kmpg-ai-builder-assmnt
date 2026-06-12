"""
Dual-LLM deliberation. For each holistic facet (fit, durability, ingenuity,
team_complement), a skeptical-hiring-manager persona and a builder-advocate persona
argue from the SAME evidence bundle. A synthesis pass surfaces where they agree,
where they don't, and what remains open.

The point is not a number. It's making disagreement legible so a human can adjudicate.
The deliberation advises; it never decides.
"""

from __future__ import annotations

from .llm import load_prompt
from .rubric import DELIBERATION_FACETS
from .schemas import Deliberation, DeliberationTurn, EvidenceBundle


def _digest(bundle: EvidenceBundle) -> str:
    return "\n".join(
        f"[{e.evidence_id}] ({e.source_label}) {e.claim_or_signal}" for e in bundle.items
    ) or "(no evidence)"


def deliberate(bundle: EvidenceBundle, llm) -> Deliberation:
    system = load_prompt("deliberate.md")
    synth_system = load_prompt("synthesize.md")
    digest = _digest(bundle)
    valid_ids = {e.evidence_id for e in bundle.items}

    facets_block = "\n".join(
        f"- id={f['id']} question={f['prompt']}" for f in DELIBERATION_FACETS
    )
    user = (
        f"#TASK:deliberate\n"
        f"Argue ALL facets below in ONE response.\n\n"
        f"FACETS:\n{facets_block}\n\n"
        f"EVIDENCE:\n{digest}\n\n"
        f"Return a JSON array, one object per facet, in the same order:\n"
        f"[{{\"id\": \"...\", \"skeptic\": \"...\", \"advocate\": \"...\", \"cites\": [...]}}]\n"
        f"cites must be evidence_ids that exist above only."
    )
    results = llm.complete_json(system=f"#TASK:deliberate\n{system}", user=user, max_tokens=4096)
    if isinstance(results, dict):
        results = results.get("facets", list(results.values()))

    results_by_id = {r["id"]: r for r in results if isinstance(r, dict) and "id" in r}

    delib = Deliberation()
    for facet in DELIBERATION_FACETS:
        r = results_by_id.get(facet["id"], {})
        cites = [c for c in r.get("cites", []) if c in valid_ids]
        delib.turns.append(DeliberationTurn(persona="skeptic", facet=facet["id"], argument=r.get("skeptic", ""), cites=cites))
        delib.turns.append(DeliberationTurn(persona="advocate", facet=facet["id"], argument=r.get("advocate", ""), cites=cites))

    transcript = "\n".join(f"[{t.persona}/{t.facet}] {t.argument}" for t in delib.turns)
    s = llm.complete_json(
        system=f"#TASK:synthesize\n{synth_system}",
        user=f"#TASK:synthesize\nDELIBERATION:\n{transcript}\n\nReturn JSON: synthesis, open_questions[].",
    )
    delib.synthesis = s.get("synthesis", "")
    delib.open_questions = s.get("open_questions", [])
    return delib
