# agent-router
Routing layer for a claims-triage agent. 4 stages: intake, extraction, policy-match,
human-approval. ~2k commits over 9 months. README documents the human-in-the-loop
approval gate and why auto-decisioning was disabled for claims over $5k.
Includes eval harness (precision/recall on 1,200 labelled claims) and a rollback
note from when v1 over-automated.
