# TruReview

**Test it here:** [t.me/KPMGassessment_bot](https://t.me/KPMGassessment_bot)

A consent-bounded, evidence-grounded evaluator for **AI Builder** candidates.

> Advisory only. This system supports a human interviewer. It does not screen,
> reject, or rank candidates without human review.

---

## The reframe (why this, not a scoring app)

Most candidate evaluators score resume polish or ask the model "is this person good?"
That fails for *this* role specifically. The KPMG brief says the differentiator for
an AI Builder is **making something real under ambiguity, with governance baked in** —
and it names the core problem out loud: *you can outsource thinking, you cannot
outsource understanding.* Now that anyone can outsource the prose, polish is noise.

So TruReview does not grade writing. It does three things:

1. **Grounds every score in evidence** the candidate actually provided.
2. **Surfaces disagreement** via a skeptic-vs-advocate deliberation, instead of an
   opaque number.
3. **Generates targeted follow-up questions at the gap between claim and evidence** —
   the exact place where outsourced thinking shows. The output serves the human
   interviewer; it does not replace them.

It also separates the failure modes the JD cares about, across a six-candidate test
matrix:

| | Real builder? | Originality signal | What it tests |
|---|---|---|---|
| **A** strong | yes | moderate | the clean "advance" |
| **B** polished buzzwords | no | low | self-described "visionary", no artifact |
| **C** self-taught, messy resume | yes | moderate–high | the gem a keyword matcher wrongly rejects |
| **D** competent but derivative | yes | **low** | ships real things, zero inventive spark |
| **E** genuine inventor | yes | **high** | the rare wedge-finder — what the role is starved for |
| **F** fluent, AI-generated | no | low | 2026's failure mode: LLM-perfect prose, hollow underneath |
| **G** real, resume doctored to JD | yes | moderate | fires the `tailored` flag — real work, engineered packaging |
| **H** resume fabricated for the role | no | — | fires `fabricated` → integrity hold (near-total mismatch + JD-shaped) |

The point of D-vs-E: both are real builders who ship. **Builder evidence alone cannot
tell them apart** — the originality cluster is what separates the journeyman from the
inventor, and that distinction is exactly what a "highest-leverage builds" pool is
hiring for. B and F both score low on originality from opposite directions (buzzwords
vs. machine-fluent slop), which is the tell that polish is not the signal.

## Authenticity layer: flag, don't penalize

Adapted from Rumate's review-classification-v3 — a gaming-vs-genuine detector — because
"is this manufactured or real?" is exactly the brief's *"you can outsource thinking, you
cannot outsource understanding."* But the scoring posture is inverted for hiring under one
locked rule:

> **The authenticity layer never subtracts from the score.** It only (a) declines to add
> credit for unsubstantiated claims — already enforced by `CriterionScore` requiring an
> evidence ref — and (b) raises **flags** for the human.

Auto-docking a candidate for "buzzwords" or "looks tailored" is an adverse-impact landmine
(everyone optimizes a resume; keyword overlap with a JD is often legitimate). Flagging
"verify this in interview" is defensible; penalizing for it is not. Eight tiers
(`classification.py`), only two of which touch the number:

| Tier | Effect | |
|---|---|---|
| `genuine` | counts | — |
| `tailored` | **flag only** | real experience (corroborates ≥~70% across the candidate's *provided* LinkedIn/portfolio), but resume doctored to the JD — keyword-mirroring, title amendments. **No discount.** |
| `unsubstantiated` (was "gaming") | **flag only** | confident claim, no artifact — earns no credit, but is *not* penalized |
| `derivative` | flag | real but tutorial-grade / one-off |
| `authorship_unclear` | flag | can't attribute the work |
| `uncertain` | flag → follow-up | route to the interviewer |
| `contradicted` | **scored** | artifact refutes the claim → the scorer scores the artifact |
| `fabricated` | **integrity hold** | the one high bar — see below |

`fabricated` requires **both** (1) *near-total* mismatch — the resume is almost entirely
absent from / contradicted by the provided sources, not one role that doesn't line up —
**and** (2) the resume is *JD-shaped* (built for this role). It requires **both
independent reviewer passes to agree** (a fairness control); a unilateral call is
downgraded to `uncertain`. Even then it never docks a penalty: the fabricated claims
simply earn no genuine credit (composite falls on its own), and the recommendation flips
to an **integrity hold** — surfaced for human verification, *never an auto-reject*. The
high bar protects the benign reasons a resume won't fully match: stale LinkedIn, name
changes, NDA'd/contract work, gaps.

Consent boundary intact: corroboration cross-checks only the candidate's **own provided**
sources. No discovery path (see below).

## The governance decision that defines the build

These agents began as BYAMN — an aggressive outreach recon system I built to apply
for this very role. The obvious move was to point that recon at applicants and
auto-enrich their profiles. **I deliberately did not.** Pointed at candidates, recon
becomes covert surveillance: it pulls in age, health, religion, politics from a
headshot or a personal blog, and creates consent and adverse-impact exposure.

So I kept the extraction muscle and **inverted the sourcing trigger**:

| | BYAMN (outreach) | TruReview (evaluation) |
|---|---|---|
| Who carries the risk | me (the sender) | the candidate |
| Sourcing | discovery — go find sources | **only links the candidate submitted** |
| Protected data | incidental | **redacted at extraction + backstop** |

There is **no discovery code path in this system, by construction.** `enrichment.py`
physically refuses any URL not in `application.provided_links`. That absence is the
control.

## Three enforced guarantees (not promises)

1. **Consent boundary** — enrichment acts only on candidate-provided links;
   `fetch_provided()` raises on anything else.
2. **Protected-characteristic redaction** — two layers: the extraction prompt refuses
   to surface/infer protected categories, and a deterministic backstop
   (`redaction.py`) neutralises leakage and logs the *category* without storing the
   *value*.
3. **Traceability** — `CriterionScore` rejects any positive score with no evidence
   reference, at construction time. Every number traces to a JD criterion and an
   artifact.

## Architecture

```
Application (resume + candidate-provided links)
  -> enrich        consent-bounded; redaction at extraction          [enrichment.py, redaction.py]
  -> score         weighted composite, each score -> JD criterion + evidence  [scoring.py, rubric.py]
  -> classify      authenticity tiers -> FLAGS (never penalties); dual-pass   [classification.py]
  -> deliberate    skeptic vs advocate over the evidence, per facet   [deliberation.py]
  -> followups     strategy finds claim-evidence gaps, draft writes Qs [followups.py]
  -> report        advisory; for human review                         [report.py]
```

The rubric (`rubric.py`) is the thinking expressed as data: 10 criteria distilled from
the JD, each with a weight, a JD anchor, and strong/weak behavioural descriptors. Tune
weights in one place; everything downstream re-traces.

### The originality cluster (originality + innovation + ingenuity)

Three criteria carry a combined **0.22** — equal to the former single top criterion —
because the brief explicitly rewards reframing the problem and finding value others
miss, and the role is "deployed against the highest-leverage builds" where the scarce
signal is not competent execution but the spark that finds the non-obvious wedge:

- **Originality** — approaches from a non-obvious angle; diverges from the default on purpose.
- **Innovation** — creates something genuinely new *that gets used*, not novelty for its own sake.
- **Ingenuity** — resourceful, elegant solutions under real constraint (no labels, no budget).

Two design decisions make this defensible rather than fluffy:

1. **Scored from evidence, never self-description.** Because `CriterionScore` rejects a
   positive score with no evidence ref, a candidate cannot score "innovative" by calling
   themselves innovative — the score must trace to an artifact showing the non-obvious
   choice. That is what makes Candidate B (buzzwords) and F (AI-generated) score *low*
   here while Candidate E (a self-calibrating disagreement-router he actually shipped)
   scores high.
2. **Translated into role-value, not left as a number.** When the cluster reads HIGH/
   MODERATE/LOW, the report emits what that *predicts for the AI Builder role* (see
   `originality_role_translation` in `scoring.py`) — and deliberately cross-references
   builder-evidence so the headline is always "invention that shipped," never novelty on
   a slide. Ingenuity also appears as a deliberation facet: the criterion scores it from
   evidence, the skeptic/advocate pass argues it holistically.

## Run it

```bash
pip install -e .                       # or: pip install anthropic pydantic
export ANTHROPIC_API_KEY=sk-ant-...
export TRUREVIEW_MODEL=<your model>    # whatever your account exposes

# Verify wiring with zero tokens first:
python -m trureview.cli --candidate data/candidates/candidate_b_polished_shallow.json --offline

# Real run (nine-candidate matrix — eight synthetic + the author):
python -m trureview.cli --candidate data/candidates/candidate_a_strong.json
python -m trureview.cli --candidate data/candidates/candidate_b_polished_shallow.json
python -m trureview.cli --candidate data/candidates/candidate_c_unconventional.json
python -m trureview.cli --candidate data/candidates/candidate_d_competent_derivative.json
python -m trureview.cli --candidate data/candidates/candidate_e_inventor.json
python -m trureview.cli --candidate data/candidates/candidate_f_ai_generated.json
python -m trureview.cli --candidate data/candidates/candidate_g_tailored.json     # fires `tailored` flag
python -m trureview.cli --candidate data/candidates/candidate_h_fabricated.json   # fires `fabricated` integrity hold
python -m trureview.cli --candidate data/candidates/candidate_i_byamn.json        # the author: genuine, HIGH originality, dual-use governance flag (see Candidate_assessment.md §6.1)
```

> Note: an isolated `.venv/` (pydantic only) is already created in this folder for the
> offline wiring check. For real runs, `pip install anthropic` into it and set
> `ANTHROPIC_API_KEY` + `TRUREVIEW_MODEL`.

Reports land in `outputs/` as both markdown and JSON.

## AI use (disclosure)

Built with an agent stack: Hermes orchestrating Claude Code (orchestration, prompts,
glue) and Codex (deterministic functions — scoring math, redaction patterns, schema).
The **decisions** were mine: the reframe away from polish-scoring, the consent-boundary
inversion, weighting governance and builder-evidence up, the claim-evidence-gap target
for follow-ups, and making redaction an enforced gate rather than a prompt hope.

## Trade-offs and what I left out (3-hour cap)

- **No live scraping / real fetch.** Enrichment reads mock pages for the provided
  links so the build is fully runnable and safe to demo. Real fetch is a TODO behind
  the identical `fetch_provided` signature — swapping it in never widens the consent
  boundary.
- **No UI.** A CLI that emits a structured markdown/JSON report is honest and faster
  than a dashboard. A thin viewer is a clean fast-follow.
- **Redaction backstop favours recall over precision** — it over-flags and logs for
  human audit rather than risking a silent miss. Defensible default for a fairness
  control.
- **Bounded deliberation** — 4 facets, one round each, for cost/latency. Multi-round
  debate is a config change.

## What I'd do next

- Real (still consent-bounded) fetch + content-type-aware extractors per link kind.
- Calibrate weights/anchors against a labelled panel of past hires.
- Inter-rater check: run the deliberation twice, flag where it's unstable.
- Bias audit harness: synthetic candidates differing only on protected proxies, assert
  scores are invariant.

## Video script (3 min)

- **0:00–0:35 — the discriminator.** Run Candidate D (competent, derivative) then
  Candidate E (the inventor). Both ship real systems — D's originality signal reads LOW,
  E's reads HIGH, and the report *translates* E's into role-value: the wedge-finder a
  highest-leverage builder pool is starved for. Builder-evidence alone couldn't separate
  them; the originality cluster does.
- **0:35–0:55 — polish is noise.** Run Candidate F (AI-generated). Fluent prose, but it
  earns no originality credit and trips the claim-evidence follow-ups — the model can't
  cite an artifact it doesn't have.
- **0:55–1:00 — the integrity moment.** Run Candidate H. The resume reads tailor-made
  for the JD; the candidate's own provided LinkedIn is medical-device sales. The tool
  raises a `fabricated` flag and flips to an **integrity hold** — then read the framing
  out loud: *surfaced for human verification, never an auto-reject*, and the score was
  never penalized, the invented claims just earned no credit. Contrast with Candidate G
  (`tailored`): real work, JD-doctored resume — **flagged, not docked.** Flash the
  redaction audit log.
- **1:00–3:00 — the thinking.** The reframe (polish is noise; probe understanding — in
  2026 the scarce signal is inventiveness, not competence). Why originality is scored
  from evidence, not self-description, and why the authenticity layer *flags but never
  penalizes* — that line between G and H is the whole responsible-AI position: auto-
  docking for "looks tailored" is an adverse-impact landmine; surfacing it for a human
  is defensible. The BYAMN lineage and the consent-boundary inversion — "there's no
  discovery path here, by construction," and corroboration only ever reads the
  candidate's *own provided* sources. The enforced guarantees. AI use + what I cut and why.
