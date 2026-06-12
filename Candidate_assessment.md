# Candidate Assessment — Design & Build Notes

**Artifact:** TruReview for AI Builder candidates
**Assignment:** KPMG AI Builder Candidate assessment (3-hour timebox, artifact + 3-min video)
**Thesis it answers:** *"You can outsource thinking, you cannot outsource understanding."*

This document is the reasoning trail behind the build: what each subsystem does, why it
exists, which existing system it was ported from, and how it serves the task. It is the
"understanding" half of the submission — the artifact is the "thinking made runnable."

> **Provenance.** Nothing in the live Rumate project was altered. Two production systems —
> the **WING/LWING weighting model** and the **TruReview dual-LLM deliberation** pattern —
> were *copied* into this isolated folder and re-pointed at a new problem: scoring AI Builder
> candidates instead of scoring buildings. The Rumate TS files were read for reference only.

---

## 0. The reframe (why this isn't a résumé scorer)

The naïve reading of the brief is "build something that scores candidates." The actual
problem the brief is pointing at is the one in its own thesis: in a world where anyone can
generate a polished, JD-perfect résumé with an LLM in ten minutes, **polish is no longer
signal — it's noise.** The scarce thing is verifiable understanding.

That is *exactly* the problem TruReview already solves in production, in a different domain.
Rumate's review-classification engine exists because anyone can buy a 5-star review; the job
is to separate **gamed polish from genuine signal**. A doctored résumé is a gamed review of
a person. So the port is not cosmetic — the underlying detection problem is identical:

| Rumate (production) | This artifact |
|---|---|
| Genuine tenant experience vs. paid/gamed reviews | Genuine builder evidence vs. LLM-polished claims |
| 7-tier gaming classification | 8-tier authenticity classification |
| Dual-LLM (Claude + Qwen) deliberation | Dual-pass deliberation, swappable to two models |
| Evidence-grounded score, gaming *flagged* not deleted | Evidence-grounded score, doctoring *flagged* not penalized |
| Corroboration across 5 independent sources | Corroboration across the candidate's own provided sources |

So the design decision that frames everything below: **the system measures understanding by
demanding evidence, and treats polish as something to surface for a human — never as something
to punish or to reward.**

---

## 1. Score weighting methodology (ported from WING/LWING)

**Files:** `trureview/rubric.py`, `trureview/scoring.py`, `prompts/score.md`

### 1.1 What WING does, and why it transfers

WING (the People's Score engine) takes many weak, noisy signals about a building, scores each
against an explicit rubric, normalizes to a common scale, and blends them with **defensible,
tunable weights** — never a black box. The whole philosophy is *"the rubric is the thinking,
expressed as data."* Change the weight in one place and everything downstream re-traces.

That is the right shape for candidate scoring too: many weak signals (résumé lines, repos,
demos), each scored against an explicit anchor, blended with weights you can defend in a room.

### 1.2 The 10 criteria (weights sum to 1.0)

Every criterion is distilled from the KPMG AI Builder (Senior Consultant) JD and carries an
explicit `jd_anchor`, a `weight`, and **behavioural descriptors** (`what_strong` / `what_weak`).
The descriptors are the load-bearing part: they are what let the scorer separate a genuine
builder from polished prose — a candidate can hit every keyword and still land "weak" because
the descriptor asks for *shipped artifacts, not claims.*

| Criterion | Weight | Why this weight |
|---|---|---|
| Builder Evidence (ships real things) | 0.18 | The JD's own thesis: the differentiator is making something real, not describing it |
| Responsible-AI / Governance Judgment | 0.15 | KPMG brand + an explicit scoring criterion; governance is a *design constraint*, not a value statement |
| Workflow & Systems Thinking | 0.14 | JD: "think in workflows, not just models" |
| Ambiguity Tolerance & Reframing | 0.12 | JD + the brief's reward for reframing the problem |
| **Originality** | **0.08** | *Originality cluster — see §4* |
| **Innovation** | **0.07** | *Originality cluster — see §4* |
| **Ingenuity** | **0.07** | *Originality cluster — see §4* |
| Enterprise Fluency | 0.07 | JD: competing stakeholder priorities, regulated constraints |
| End-to-End Ownership / Lifecycle | 0.07 | JD: prototype → productionize → maintain |
| Reusability & Leverage | 0.05 | JD: "contribute reusable skills so each build starts further ahead" |

Governance and builder-evidence are weighted **up** on purpose: it's KPMG's brand and an
explicit criterion (governance), and it's the JD's central claim (evidence over description).
The **originality cluster carries a combined 0.22** — equal to the former single top
criterion — because the brief explicitly rewards finding value others miss (§4).

### 1.3 How a score is produced (and why it's auditable)

`score_candidate()` loops the criteria; for each, the LLM scores **0–5 against the anchor and
descriptors** and must **cite `evidence_ids` that actually exist** in the bundle. Then:

```
composite_0_100 = Σ (weight × score/5) × 100
```

**The grounding guard (the single most important line in the scorer):**

```python
# Guard: can't claim a positive score with no surviving evidence ref.
if raw_score > 0 and not refs:
    raw_score = 0.0
```

and the same invariant is enforced *structurally* at the schema layer so a downstream agent
can't bypass it — `CriterionScore` raises at construction time if `score_0_5 > 0` with no
`evidence_refs`. **"Auditable by design" is enforced, not promised.** This is how the system
measures understanding: a confident claim with nothing inspectable behind it scores zero, not
because it was punished, but because there was nothing to credit.

### 1.4 Recommendation bands are advisory, never a gate

`recommendation_band()` maps the composite to an interviewer *next-action* ("Advance — strong
signal", "Borderline — follow-ups are decisive"), never an accept/reject. The schema has **no
auto-accept/reject field at all.** Nothing in this system screens a human out.

---

## 2. Dual-LLM classification (ported from TruReview deliberation)

**Files:** `trureview/classification.py`, `prompts/classify.md`, `trureview/deliberation.py`

There are **two** dual-LLM mechanisms in the build, both descended from the Rumate
`resolveDualClassification` / `t6-deliberation` patterns. They do different jobs.

### 2.1 The authenticity classifier — two opposing stances, reconciled

`classify_candidate()` runs **two independent passes over the same materials with opposing
stances**:

- a **skeptical** pass — "default to doubt; demand corroboration before crediting a claim"
- a **charitable** pass — "give benefit of the doubt where experience plausibly tracks"

Each pass returns a `corroboration_pct` and a list of typed `flags`. `_reconcile()` then merges
them deterministically — the same way TruReview's conflict-resolution rules merge Claude and
Qwen, rather than averaging into mush:

- **Corroboration %** = mean of the two passes.
- **Flags favour recall** — a flag raised by *either* pass survives (we'd rather surface a
  concern for the human than suppress it).
- **`fabricated` requires BOTH passes to reach it independently** — the fairness bar. A
  unilateral `fabricated` from one stance is **downgraded to `uncertain`** with a note. One
  skeptical reviewer alone can never trigger an integrity hold.

This is the production lesson ported directly: in Rumate the **calibrated** model (Qwen, 76%)
overrides the **miscalibrated** one (Haiku, 62%) on specific conflict types rather than
democratic averaging. Here, the *high-stakes* verdict (fabrication) requires agreement, and
the *low-stakes* verdicts (everything to surface) favour recall. The reconciliation is
deterministic and inspectable, not a third LLM call.

> **Model-swappable by design.** Both passes currently run over one model with opposing
> stances. Swapping the second pass to a genuinely different model (e.g. Qwen, exactly as
> Rumate does) is a one-call change behind the same `llm.complete_json` interface — the
> reconciliation logic does not change. The stance-diversity gives most of the benefit of
> model-diversity at zero extra dependency for the demo.

### 2.2 The holistic deliberation — skeptic vs advocate

`deliberate()` is the second, separate mechanism: for each **facet** (`fit`, `durability`,
`ingenuity`, `team_complement`) a **skeptical hiring-manager** persona and a **builder-advocate**
persona argue *from the same evidence bundle*, then a synthesis pass surfaces where they agree,
where they don't, and what's still open.

The point of this layer is **not a number** — it's making disagreement *legible* so a human
can adjudicate. This is the deliberation pattern doing what it does in TruReview: surfacing the
tension instead of hiding it inside a single confident score.

---

## 3. Resume doctoring for the JD + LinkedIn context backfill and match

**Files:** `prompts/classify.md`, `trureview/classification.py` (`KPMG_AI_BUILDER_JD`,
`_source_digest`), `trureview/enrichment.py` (the consent boundary)

This is the heart of the candidate-specific work and the part with no direct Rumate analog —
it's the *inversion* of one.

### 3.1 The corroboration check ("LinkedIn context backfill and match")

For each candidate, `_source_digest()` assembles the résumé **plus the content of every link
the candidate themselves provided** (LinkedIn, portfolio, repos, personal site). The classifier
estimates `corroboration_pct`: **how much of the résumé's substantive experience is
corroborated across the candidate's own provided sources.**

This is the "backfill and match" mechanism: the résumé is the *claim*; LinkedIn/portfolio/repos
are the *context* it's matched against. The match is what tells `tailored` (real person, doctored
packaging — ~70%+ corroboration) apart from `fabricated` (near-total mismatch — a résumé and a
career that read as two different people).

### 3.2 The doctoring detector — `tailored` vs `fabricated`

The 8-tier scheme (`prompts/classify.md`) classifies notable claims. The two tiers that matter
for doctoring:

- **`tailored`** — the experience *broadly corroborates* across provided sources, BUT the
  résumé is doctored to the JD: same keywords as the JD, job titles amended/inflated to match
  the requirements, responsibilities reworded to mirror JD bullets. **Real person, engineered
  packaging.** → **FLAG ONLY. Never a score hit.** Tailoring a résumé to a job is normal,
  rational candidate behaviour; we surface it so the interviewer reads the titles with
  appropriate skepticism, but we do not punish a real builder for good packaging.

- **`fabricated`** — a deliberately **HIGH bar** requiring BOTH:
  1. **near-total mismatch** — the résumé's experience is almost entirely absent from or
     contradicted by the provided sources (NOT merely one role that doesn't line up), AND
  2. **JD-shaped** — the résumé reads as built specifically for this job description.

  If only one holds, it is *not* fabricated — it routes to `uncertain` / `authorship_unclear`.
  Benign reasons a résumé won't fully match (stale LinkedIn, name change, NDA'd/contract work,
  career gaps) produce a "near-total mismatch, verify" flag — **never** a fabrication
  conclusion on thin grounds.

`KPMG_AI_BUILDER_JD` is held in the classifier as the reference text the résumé's language is
checked against for keyword-mirroring and title-amendment signals.

### 3.3 Why doctoring is flagged, not penalized (the responsible-AI position)

This is the deliberate ethical stance and the strongest governance argument in the submission.
A penalty model that docks points for "JD-mirroring keywords" would:

- punish ESL candidates and career-changers who legitimately mirror a JD to be legible,
- create disparate impact with no way to audit it, and
- turn the tool into an adverse-impact engine that quietly screens people out.

So the **authenticity layer never subtracts from the score**, by locked design. It does two
things only: (a) declines to *add* credit for unsubstantiated claims (already enforced by the
evidence-grounding guard in §1.3), and (b) raises flags for the human. Only two tiers touch
the number at all:

- **`contradicted`** — the scorer already scores the *artifact*, not the claim, so reality is
  already priced in.
- **`fabricated`** — fabricated claims earn no genuine credit upstream (so the composite falls
  *naturally*, no arbitrary penalty), and the recommendation flips to an **integrity hold** —
  still advisory, still human-owned, surfaced and never an auto-reject.

The contrast the system is built to draw cleanly: **Candidate G (tailored) is flagged but keeps
their score; Candidate H (fabricated) trips the integrity hold.** That single pair on screen
*is* the demonstration of "competing stakeholder priorities" judgment the brief asks for — catch
the fabricator, but don't let the tool become an auto-rejecting machine.

### 3.4 The consent boundary (the governance invariant)

**File:** `trureview/enrichment.py`

The corroboration check cross-references **only links the candidate explicitly provided.** There
is no discovery path anywhere in the codebase — no function searches for, or goes looking for,
sources about a person. `fetch_provided()` hard-raises `PermissionError` on any URL not in
`application.provided_links`, and `Application` has **no field** that could hold a discovered
source. *The absence is the design.*

> **Lineage (the reframe, made concrete).** These extraction agents began as **BYAMN**
> aggressive outreach recon — built to *find* everything about a target. The exact same
> extraction muscle is reused here, but the **sourcing trigger is inverted**: in outreach the
> risk sat on the sender; in evaluation the risk sits on the *candidate*, so discovery is
> removed and only consented links are deep-dived. Reusing an aggressive tool *with the
> consent boundary inverted* is itself the responsible-AI argument the brief rewards.
>
> BYAMN is a real, public system — and its author is **Candidate I** in the matrix (§6.1),
> evaluated by the very system built from inverting it. That recursion is the artifact's apex case.

---

## 4. Ingenuity, innovation, creativity "buffs" — the originality cluster + few-shots

**Files:** `trureview/rubric.py` (`ORIGINALITY_CLUSTER`, `DELIBERATION_FACETS`),
`trureview/scoring.py` (cluster → signal → role translation)

This is the additive layer the assignment specifically called for: scoring **originality,
innovation, ingenuity**, and translating them into AI-Builder role-value.

### 4.1 Three distinct criteria, not one fuzzy "creativity"

| Criterion | What it measures | Strong looks like |
|---|---|---|
| **Originality** (0.08) | Non-obvious *approach* | A path a competent peer would NOT default to — a reframing, an unconventional architecture, a problem redefined before it was solved |
| **Innovation** (0.07) | Creates something *new that's used* | A capability/combination that didn't exist before AND created real, adopted value — not novelty for its own sake |
| **Ingenuity** (0.07) | Resourceful *under constraint* | Solved a hard problem elegantly with no labels/budget/time, rather than brute force |

Splitting "creativity" into three is what makes the signal usable: a candidate can be highly
*ingenuous* (resourceful under constraint) while being *un-original* (textbook approach), and
the report says so instead of collapsing it into one vague star rating.

### 4.2 The "buff" is grounded, never a self-declaration

The cluster carries real weight (0.22 combined — the highest of any single concept) — **but it
is scored from EVIDENCE like every other criterion.** A candidate who writes "innovative
visionary" with no artifact behind it scores **0** here, caught by the same grounding guard
(§1.3) and the schema validator. This is the deliberate defense against the failure mode the
brief warns about: an LLM-polished résumé *claiming* originality is the easiest thing in the
world to generate; the score only moves if an artifact shows the non-obvious choice.

This is the originality cluster's version of TruReview's core move — **invention that shipped is
the signal, novelty on a slide is noise.**

### 4.3 Cluster → signal → role translation

`scoring.py` reads the three criteria together:

```
originality_cluster_0_5()  → weight-blended mean (0–5)
originality_signal()       → HIGH (≥4.0) | MODERATE (≥2.5) | LOW
originality_role_translation() → what it predicts for THIS role
```

`originality_role_translation()` answers the assignment's actual question — *"if a candidate
scores on those, what does it mean for an AI Builder?"* The HIGH translation is deliberately
**cross-referenced to Builder Evidence** so novelty alone is never the headline: *"read
alongside Builder Evidence: reward invention that shipped and was used, not cleverness on a
slide. If both are high, prioritise."* A HIGH-originality candidate is framed as the rare,
high-leverage builder who *"finds the non-obvious wedge … and invents reusable primitives that
compound across every downstream build."*

### 4.4 Ingenuity also runs as a deliberation facet (intentional double-coverage)

`ingenuity` appears **both** as a rubric criterion (scored from evidence) *and* as a
`DELIBERATION_FACET` (argued holistically by skeptic vs advocate). On purpose: the criterion
scores the concrete artifact; the facet asks the open-ended panel question *"is there a genuine
spark of inventiveness, or competent execution of known patterns?"* The number and the argument
check each other.

### 4.5 Few-shots — dynamic, adapted from review-classification-v3

The Rumate `review-classification-v3.ts` engine uses `FEW_SHOT_EXAMPLES` + `selectFewShotExamples`
+ `buildClassificationPrompt` to **dynamically inject the most relevant labelled examples** into
each classification call rather than a static block — the production lesson being that few-shot
*selection* (matching exemplars to the case at hand) is what calibrated the dual model and
resolved the 45 Haiku/Qwen disagreements.

In this artifact the same principle is carried in two ways:

- **Behavioural descriptors as inline exemplars.** Each rubric criterion's `what_strong` /
  `what_weak` pair functions as a compact, always-present few-shot: it shows the scorer the
  *shape* of a 5 vs a 0 for that specific competency, which is what keeps "hit every keyword,
  still scored weak" working.
- **Tier definitions as classification exemplars.** `prompts/classify.md` carries a worked
  example inside each tier (e.g. `contradicted`: *"'owned end-to-end' but the repo shows a
  handful of one-day commits"*) — the doctoring detector's few-shots, adapted from the gaming
  exemplars in v3.

The dynamic-selection harness (`selectFewShotExamples`) is the documented next step for a
real-LLM run: it slots in behind `buildClassificationPrompt` without changing any caller, exactly
as it does in production — the place to grow this if the candidate pool widens.

---

## 5. Things easy to miss (the rest of the end product)

These are the supporting pieces that make the above trustworthy rather than a demo trick.

- **Redaction / protected-category scrubbing** (`trureview/redaction.py`, `enrichment.py`).
  Two-layer: the extraction prompt is told the protected categories, and `scrub()` is a
  backstop. Every report carries a **redaction audit log** that records *what category was
  stripped without storing the protected value* (e.g. "stripped probable age signal from About
  page"). Fairness is logged, not assumed.

- **Schemas encode governance structurally** (`schemas.py`). The posture can't be quietly
  bypassed by a downstream agent: no discovery field on `Application`; `CriterionScore` rejects
  ungrounded scores at construction; `Report` has no auto-accept/reject field and ships a
  standing disclaimer that it *must not be used to auto-screen, auto-reject, or rank without
  human review.*

- **Offline-runnable by construction** (`llm.py` `StubLLM`, `data/mock_pages/`). The whole
  pipeline runs with **zero tokens and no network** via a `#TASK:<tag>` system-prompt convention
  and local mock pages — so the artifact is fully demonstrable in the timebox. Swapping to
  `AnthropicLLM` (set `ANTHROPIC_API_KEY` + `TRUREVIEW_MODEL`, `pip install anthropic`) is a
  config change, not a code change, behind the identical interface — the same discipline that
  keeps the consent boundary from widening when mock→real.

- **The pipeline order is the argument** (`pipeline.py`):
  `enrich (consent-bounded) → score (traceable) → classify (dual-pass authenticity) →
  deliberate (dual-LLM) → follow-ups → report (advisory)`. Enrichment is first *and* boundaried;
  scoring is grounded before any authenticity verdict; classification can only *flag*; the report
  is explicitly advisory. The flow itself enforces the ethics.

- **Targeted follow-ups** (`followups.py`). The system's output isn't a verdict, it's *better
  questions for the human interviewer* — each follow-up names the gap type, the claim it targets,
  and what a strong answer would show. This is the "serve the human, don't replace them" stance
  made concrete.

---

## 6. The candidate matrix (what the demo proves)

Nine candidates — **eight synthetic, plus one real: the author** — are designed so that **each
subsystem fires on at least one**, and so the two hardest discriminations are shown side by side:

| Candidate | Designed to exercise | Expected result |
|---|---|---|
| A — strong | Grounded builder evidence | Advance — high composite |
| B — polished, shallow | Buzzwords, no artifacts | Low score via grounding guard, NOT a penalty |
| C — unconventional | Reframing under ambiguity | Originality signal without polish |
| D — competent derivative | Real but textbook | LOW originality — the discriminator vs E |
| E — inventor | Genuine non-obvious invention | **HIGH originality** — the cluster's reason to exist |
| F — AI-generated | LLM-slop polish | No originality credit; trips follow-ups |
| G — tailored | Real (~70%+ corroborated), JD-doctored | **`tailored` flag, score intact** |
| H — fabricated | Near-total mismatch, JD-shaped | **Integrity hold** (both passes agree) |
| **I — Wells Mensah (real / BYAMN)** | **Reframe + HIGH originality cluster + a real governance flag on a genuine candidate** | **Advance, top of pool; `genuine`, high corroboration; dual-use governance flag surfaced, score intact** |

**D vs E** proves the originality cluster does work evidence alone can't (two real builders,
separated by inventiveness). **G vs H** proves the responsible-AI line: doctoring is surfaced
without punishment; only near-total fabrication trips a hold — and even that is advisory, never
an auto-reject. **I is the apex case (§6.1)** — the only real candidate, and the one that closes
the loop the whole artifact is built around.

### 6.1 The apex case — the candidate who built BYAMN *and* TruReview

Candidate I is not synthetic. It is the author of this system, evaluated by this system, on a
public artifact anyone can open: **BYAMN** (`github.com/WellsatRumate/byamn-agent`) — a 5-agent
outreach system built as a proof-of-work application for *this exact KPMG role*, on the premise
*"the agent is the application."* Rather than write a cover letter about building agents, he
built one that researches the hiring team, finds a route to them, drafts outreach, and — with
his approval — sends it, signing every message as AI-built and linking the repo so the recipient
can verify.

It earns a top score honestly, because the artifact is **inspectable** — the whole point of the
scorer (§1.3). Each criterion traces to the public repo and build log, not to self-description:

- **Builder Evidence** — a runnable 5-agent system with a documented six-version build log; plus
  Rumate, a shipped production platform. Among the strongest in the pool.
- **Ambiguity & Reframing** — the canonical example: he redefined "apply for the job" into
  "build the agent the job asks for, and let it apply." The brief explicitly rewards reframing;
  this is the reframe.
- **Originality cluster → HIGH.** *Originality:* a path no competent peer defaults to. *Innovation:*
  it was **used and it worked** — git-commit email-dorking surfaced a personal address scrapers
  never return, which produced a genuine "please apply" reply he then referenced on the live
  application. Real, adopted value, not novelty on a slide. *Ingenuity:* resourceful under a hard
  constraint — multi-path routing (a teammate's own website chatbot, a podcast-collaboration form
  on the hiring manager's platform), a self-recording proof loop (records its run → uploads to its
  own Drive → drops the link in the copy), and a ~7-hour build that routed around a dead OSINT API.
- **Governance — and the flag that makes the entry stronger, not weaker.** The honest move is to
  surface, not suppress, the dual-use tension: BYAMN performs genuinely aggressive recon on real
  people. The system flags it for the human **without docking the score** — exactly the posture
  of §3.3. And the governance score is *high on the merits*, because the candidate built the
  boundary in: **disclosure not deception** (every message self-identifies as AI), **human-in-the-
  loop** (nothing sends without approval), **privacy partitioning** (live target dossiers kept in
  a private repo), and **licensing hygiene** (GPL-3 quarantined from the MIT repo).

**Why this is the apex demonstration of the whole artifact.** The evaluator was built by
*inverting BYAMN's consent boundary* — taking the same recon agents and removing their discovery
path so TruReview only ever reads a candidate's own provided links (§3.4). So Candidate I is the
recursive proof: the gaming-detector built to catch outsourced polish meets the one candidate who
built both the aggressive tool *and* its ethical inversion — and instead of catching a faker, it
correctly reports a genuine, high-originality builder with one governance conversation worth having
in the interview. That is the entire thesis in a single case: **understanding can't be outsourced,
and the right response to a real concern is to surface it for a human, never to auto-reject.**

> Run it: `python -m trureview.cli --candidate data/candidates/candidate_i_byamn.json`
> (offline gives the flat stub score like every candidate; a live key produces the differentiated
> result described above).

---

## 7. One-line summary

> The artifact takes two systems that already separate *genuine signal from gamed polish* in
> production, inverts a recon tool's consent boundary to put the risk on the right party, scores
> candidates **only** on evidence you can open, treats résumé-doctoring as something to **surface
> for a human rather than punish**, and adds an originality cluster that rewards **invention that
> shipped, not novelty that was claimed.** It measures understanding by refusing to credit
> anything it can't inspect — which is the brief's whole thesis, made runnable.
