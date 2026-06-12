"""
Data contracts for TruReview.

These schemas are not just typing sugar. They encode the governance posture
structurally, so the boundaries can't be quietly bypassed by a downstream agent:

  * Application has NO "search for this person" field. Enrichment can only ever
    act on candidate-provided links. The absence is the point.
  * CriterionScore REQUIRES evidence_refs. A score that points at no evidence is
    rejected at construction time. "Auditable by design" is enforced, not promised.
  * Report is explicitly advisory. There is no auto-accept/reject field.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, model_validator


class ProvidedLink(BaseModel):
    label: str
    url: str
    kind: str  # repo | demo | portfolio | writing | other


class Application(BaseModel):
    candidate_id: str
    display_name: str  # pseudonymized handle is fine; we don't need a legal name to evaluate work
    role_level: str = "Senior Consultant"
    resume_text: str
    provided_links: list[ProvidedLink] = Field(default_factory=list)
    # Deliberately absent: any field that would let the system go discover sources
    # about this person. Enrichment is consent-bounded to provided_links only.


class EvidenceItem(BaseModel):
    evidence_id: str
    source_label: str           # which provided link, or which resume section
    source_url: Optional[str] = None
    claim_or_signal: str        # job-relevant signal, post-redaction
    relevance: str              # why this maps to a builder competency
    redacted: bool = False      # True if redaction removed protected content from this item


class EvidenceBundle(BaseModel):
    candidate_id: str
    items: list[EvidenceItem] = Field(default_factory=list)
    # Human-readable audit trail of what redaction stripped, WITHOUT storing the
    # protected value itself. e.g. "Stripped probable age signal from 'About' page."
    redaction_log: list[str] = Field(default_factory=list)

    def by_id(self, evidence_id: str) -> Optional[EvidenceItem]:
        return next((e for e in self.items if e.evidence_id == evidence_id), None)


class CriterionScore(BaseModel):
    criterion_id: str
    criterion_name: str
    weight: float
    score_0_5: float
    evidence_refs: list[str] = Field(default_factory=list)
    rationale: str

    @model_validator(mode="after")
    def _scores_must_be_grounded(self) -> "CriterionScore":
        # A non-zero score must cite at least one evidence item. The only legitimate
        # ungrounded score is an explicit zero meaning "no evidence was provided".
        if self.score_0_5 > 0 and not self.evidence_refs:
            raise ValueError(
                f"Criterion '{self.criterion_id}' scored {self.score_0_5} with no "
                f"evidence_refs. Scores must trace to evidence."
            )
        if not (0.0 <= self.score_0_5 <= 5.0):
            raise ValueError("score_0_5 must be in [0, 5].")
        return self


class DeliberationTurn(BaseModel):
    persona: str   # "skeptic" | "advocate"
    facet: str     # fit | durability | ingenuity | team_complement
    argument: str
    cites: list[str] = Field(default_factory=list)  # evidence_ids


class Deliberation(BaseModel):
    turns: list[DeliberationTurn] = Field(default_factory=list)
    synthesis: str = ""
    open_questions: list[str] = Field(default_factory=list)


class FollowUp(BaseModel):
    target_claim: str
    gap_type: str  # claim_without_evidence | high_polish_low_artifact | unverified_scope | depth_probe
    question: str
    what_a_strong_answer_shows: str


class Flag(BaseModel):
    """An authenticity/integrity concern surfaced for the human reviewer.

    Flags do NOT penalize the score. Only `contradicted` (the scorer already scores
    the artifact) and `fabricated` (no genuine credit + integrity hold) touch the
    number; every other tier is score-neutral and exists purely to be surfaced.
    """
    tier: str          # genuine|tailored|contradicted|derivative|unsubstantiated|authorship_unclear|uncertain|fabricated
    claim: str         # the resume claim / evidence under question
    why: str           # why it was classified this tier
    what_to_verify: str = ""   # concrete next action for the interviewer
    affects_score: bool = False  # True only for contradicted & fabricated


class ClassificationOutcome(BaseModel):
    """Result of the authenticity pass. Advisory; feeds flags into the Report."""
    flags: list[Flag] = Field(default_factory=list)
    corroboration_pct: Optional[float] = None  # how much of the resume corroborates across provided sources
    integrity_hold: bool = False               # True only on the high-bar `fabricated` case


class Report(BaseModel):
    candidate_id: str
    display_name: str
    composite_score: float          # 0-100
    recommendation: str             # advisory band only
    criterion_scores: list[CriterionScore]
    deliberation: Deliberation
    follow_ups: list[FollowUp]
    # Originality cluster (originality + innovation + ingenuity), read together and
    # translated into role-value. Advisory, like everything else.
    originality_cluster_0_5: float = 0.0
    originality_signal: str = ""    # HIGH | MODERATE | LOW
    originality_role_translation: str = ""
    # Authenticity flags (advisory). Composite is NOT penalized by these; see Flag.
    flags: list[Flag] = Field(default_factory=list)
    corroboration_pct: Optional[float] = None
    integrity_hold: bool = False
    redaction_log: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "Advisory only. Generated to support a human interviewer's judgment. "
        "This system does not make hiring decisions and must not be used to "
        "auto-screen, auto-reject, or rank candidates without human review."
    )
