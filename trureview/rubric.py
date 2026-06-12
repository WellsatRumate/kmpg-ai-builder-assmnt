"""
The rubric IS the thinking, expressed as data.

Every criterion is distilled from the KPMG AI Builder (Senior Consultant) JD and
carries an explicit JD anchor, a weight, and behavioural descriptors for what
strong vs weak looks like. The descriptors are what let the scorer separate
genuine builders from polished prose: a candidate can hit every keyword and still
land "weak" because the descriptors ask for shipped artifacts, not claims.

Weights sum to 1.0. They reflect a defensible prioritization for THIS role:
governance and real builder-evidence are weighted up because (a) it's KPMG's
brand and an explicit scoring criterion, and (b) the JD's own thesis is that the
differentiator is making something real under ambiguity, not describing it.

An ORIGINALITY CLUSTER (originality + innovation + ingenuity) carries a combined
0.22 — equal to the former single top criterion — because the assignment brief
explicitly rewards reframing the problem and finding value others miss, and the
role is "deployed against the highest-leverage builds" where the scarce signal is
not competent execution of known patterns but the spark that finds the non-obvious
wedge. Crucially these are scored from EVIDENCE like every other criterion: a
candidate cannot score "innovative" by calling themselves innovative (see Candidate
B/F) — the score must trace to an artifact showing the non-obvious choice. That is
what separates genuine inventiveness from a buzzword.

Tune the weights in one place; everything downstream re-traces automatically.
"""

CRITERIA: list[dict] = [
    {
        "id": "builder_evidence",
        "name": "Builder Evidence (ships real things)",
        "weight": 0.18,
        "jd_anchor": "Builder mindset — don't just describe solutions, you create them.",
        "what_strong": "Points to specific shipped artifacts: repos, demos, live systems, "
                       "things real users touched. Claims are backed by inspectable work.",
        "what_weak": "Describes solutions in the abstract. Lots of 'led', 'drove', "
                     "'transformed' with no artifact you can open and verify.",
    },
    {
        "id": "governance",
        "name": "Responsible-AI / Governance Judgment",
        "weight": 0.15,
        "jd_anchor": "Treat risk, governance, ethics, and trust as core design constraints, "
                     "not afterthoughts.",
        "what_strong": "Names concrete constraints they designed around (privacy, consent, "
                       "human review, auditability) and what they deliberately did NOT build.",
        "what_weak": "Governance mentioned only as a value statement, with no design "
                     "decision attached to it.",
    },
    {
        "id": "workflow_systems",
        "name": "Workflow & Systems Thinking",
        "weight": 0.14,
        "jd_anchor": "Think in workflows, not just models — human-AI handoffs, decision "
                     "boundaries, appropriate autonomy.",
        "what_strong": "Designs multi-step processes with explicit handoffs, failure modes, "
                       "and where the human stays in the loop.",
        "what_weak": "Model-centric. Talks about prompts/models but not the surrounding "
                     "process, handoffs, or boundaries.",
    },
    {
        "id": "ambiguity_reframe",
        "name": "Ambiguity Tolerance & Reframing",
        "weight": 0.12,
        "jd_anchor": "Comfortable operating in ambiguity; turn a vague prompt into a "
                     "concrete, defensible direction.",
        "what_strong": "Shows a case where they redefined the problem, made assumptions "
                       "explicit, and committed to a direction under uncertainty.",
        "what_weak": "Waits for fully-specified problems. No evidence of self-directed "
                     "scoping or reframing.",
    },
    # --- ORIGINALITY CLUSTER (combined 0.22) -------------------------------------
    # The scarce, highest-leverage signal for this role. Scored from EVIDENCE, never
    # from self-description: a candidate who writes "innovative visionary" with no
    # artifact behind it scores 0 here (see schemas.py — positive score needs a ref).
    {
        "id": "originality",
        "name": "Originality (non-obvious approach)",
        "weight": 0.08,
        "jd_anchor": "Identify where AI creates value others miss; reframe the problem "
                     "(assignment brief) — commit to a non-obvious direction under ambiguity.",
        "what_strong": "Evidence shows a path a competent peer would NOT have defaulted to — "
                       "a reframing, an unconventional architecture, a problem redefined before "
                       "it was solved. Divergence from the obvious reference solution, on purpose.",
        "what_weak": "Reaches for the textbook/default. Competent but predictable; the approach "
                     "is the first one anyone would name. No divergence from the reference pattern.",
    },
    {
        "id": "innovation",
        "name": "Innovation (creates something new that's used)",
        "weight": 0.07,
        "jd_anchor": "Move beyond experimentation to validate NEW agentic capabilities; "
                     "connect pain points to practical, value-driven implementations.",
        "what_strong": "Produced something genuinely new in their context — a capability, "
                       "application, or combination that did not exist before — AND it created "
                       "real value (adopted, used, measurable), not novelty for its own sake.",
        "what_weak": "Re-implements what already exists. Useful delivery of known patterns, but "
                     "nothing new is created; the 'innovation' is incremental at best.",
    },
    {
        "id": "ingenuity",
        "name": "Ingenuity (resourceful under constraint)",
        "weight": 0.07,
        "jd_anchor": "Make reasonable assumptions and build quickly under real constraint — "
                     "elegant solutions when time, data, or budget are scarce.",
        "what_strong": "Solved a hard problem resourcefully under a real constraint (no labels, "
                       "no budget, legacy system, tight clock) with a clever or elegant approach "
                       "rather than brute force or throwing resources at it.",
        "what_weak": "Solutions work but are heavy-handed, or only possible with ample resources. "
                     "No evidence of clever constraint-navigation; would stall when resources thin.",
    },
    # -----------------------------------------------------------------------------
    {
        "id": "enterprise_fluency",
        "name": "Enterprise Fluency",
        "weight": 0.07,
        "jd_anchor": "Enterprise fluency — understands how organizations operate, competing "
                     "stakeholder priorities.",
        "what_strong": "Demonstrates understanding of stakeholders, regulated constraints, "
                       "and what 'production' means when reputation is on the line.",
        "what_weak": "Pure individual-contributor framing with no sense of organizational "
                     "context or competing priorities.",
    },
    {
        "id": "ownership_lifecycle",
        "name": "End-to-End Ownership / Lifecycle",
        "weight": 0.07,
        "jd_anchor": "Own the full build lifecycle: prototype, productionize, maintain.",
        "what_strong": "Carried something from problem definition through to a working system "
                       "people used, and stayed with it past the demo.",
        "what_weak": "Hands off at the prototype boundary; no evidence of productionizing or "
                     "maintaining.",
    },
    {
        "id": "reusable_leverage",
        "name": "Reusability & Leverage",
        "weight": 0.05,
        "jd_anchor": "Contribute reusable skills, components, and tools so each build starts "
                     "further ahead.",
        "what_strong": "Builds components/patterns others can reuse; thinks about compounding "
                       "leverage, not one-off scripts.",
        "what_weak": "Every build is bespoke and throwaway; no abstraction or shared asset "
                     "thinking.",
    },
]

# The originality cluster, surfaced separately in the report and translated into
# role-value. Ingenuity also appears as a deliberation facet below — the criterion
# scores it from evidence; the facet argues it holistically. Both, on purpose.
ORIGINALITY_CLUSTER: list[str] = ["originality", "innovation", "ingenuity"]

# Facets the dual-LLM deliberation argues over (distinct from rubric criteria:
# criteria score the resume; facets are the holistic interview-panel questions).
DELIBERATION_FACETS = [
    {
        "id": "fit",
        "prompt": "Does the evidence show fit for a hands-on AI Builder in a regulated "
                  "enterprise, vs a describer or a pure researcher?",
    },
    {
        "id": "durability",
        "name": "durability",
        "prompt": "Will this person hold up across the full lifecycle and ambiguity, or do "
                  "they fade once the problem stops being greenfield?",
    },
    {
        "id": "ingenuity",
        "prompt": "Is there a genuine spark of inventiveness in how they solve problems, or "
                  "competent execution of known patterns?",
    },
    {
        "id": "team_complement",
        "prompt": "What does this person add that a team of strong builders might lack? Where "
                  "would they be redundant?",
    },
]


def weight_check() -> float:
    return round(sum(c["weight"] for c in CRITERIA), 4)
