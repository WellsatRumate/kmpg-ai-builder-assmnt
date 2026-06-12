# GitHub — WellsatRumate/byamn-agent

**BYAMN — By Any Means Necessary.** A 5-agent AI outreach system built by Wells Mensah as a
proof-of-work application for the KPMG Canada AI Builder (Senior Consultant) role. README
opening line: *"The agent IS the application."* Every outreach message the system sends links
back to this repo so the recipient can verify the message was drafted and sent by an AI agent,
not a human disguised as one.

## Inspectable contents (public)
- `CLAUDE.md` — the system prompt / brain; Claude Code reads it on session start.
- `BYAMN_Build_Spec_Agents.md` — full architecture, pipeline, demo plan.
- `HOW-IT-WAS-MADE.md` — build log of the ~7-hour, two-day sprint; documents six architecture
  versions (v1 single script → v6), real failure modes (dead Osintgram API, blocked Apify
  actors on free tier) and the workarounds.
- `modes/` — per-agent system prompts: recon, deep-recon, strategy, draft, campaign, browse.
- `scripts/` — `apify-recon.mjs`, `deep-recon.mjs` (entity + contact extraction, target
  discovery, connection mapping, **intake-vector discovery**), `osint-ig.mjs`, `send-gmail.mjs`,
  `browse.mjs`, plus Vercel's `agent-browser` Rust CLI for dynamic/unknown pages.
- `playbooks/browser-routing.md` — decision logic for Playwright (known selectors) vs
  agent-browser (snapshot-driven, adaptive) per target site.
- `Wells_Mensah_CV.pdf`, `cover-letter.md` — the human application alongside the agent.

## The 5-agent architecture (real, runnable)
```
Recon → Deep Recon → Strategy → Draft → Campaign (orchestrator)
                                         ↓  Gmail / Playwright / agent-browser
```
Claude Code is the reasoning layer; the scripts are non-LLM data gatherers and executors.
Recon and Deep Recon run sequentially; Strategy and Draft can overlap; Campaign manages state,
presents drafts for approval, executes, and logs.

## What it actually did (corroborates the résumé's specific claims)
- **Git-commit email discovery:** email-dorking over a target's public commit history surfaced
  a personal address that LinkedIn/Apify scrapers never return. That route produced a genuine
  "please apply" reply, later referenced on the live application.
- **Chatbot route:** reached a second team member through their own website's chatbot via the
  adaptive agent-browser path.
- **Podcast-form route:** reached a third via a collaboration form on the hiring manager's
  career-coaching platform.
- **Self-recording proof loop:** headed Playwright records its own browser runs; the video is
  uploaded to the agent's own Google Drive and the link is embedded in the outreach copy.

## Governance, designed in (not bolted on)
- **Disclosure, not deception:** every Gmail send appends a signature — *"This message was
  researched, drafted, and sent by BYAMN, an AI outreach agent purpose-built by Wells Mensah"* —
  and links this repo so recipients can verify.
- **Human-in-the-loop:** the Campaign agent presents every draft for Wells's approval; nothing
  sends autonomously.
- **Privacy gating:** real target lists, dossiers, and the live campaign log are kept in a
  PRIVATE repo. README states publishing recon output on people in a campaign-in-flight would
  compromise them "regardless of how public their LinkedIn profiles are." Public repo ships the
  schema and methodology; not the live data.
- **Licensing hygiene:** the GPL-3 OSINT tool is quarantined as a git submodule, kept clear of
  the MIT-licensed main repo.

## Note for an evaluator
This is genuinely aggressive outreach recon — it discovers personal contact paths and routes
into people. It is also disclosed, human-gated, and privacy-partitioned. The dual-use tension
is real and is the exact responsible-AI judgment the role exists to exercise. The same author
built TruReview (the system reading this) by inverting BYAMN's consent boundary so it only ever
reads a candidate's own provided links.
