# Rumate — Intelligence (rumate.io/intelligence)

Live institutional page for **Rumate**, a housing-trust intelligence platform: *"What FICO did
for credit, Rumate does for buildings."* B2C2G — an AI tenant assistant (Tori) generates
building-level intelligence that is aggregated for municipalities, insurers, and lenders.

Corroborates the résumé's Rumate claims with a real, reachable product surface:
- Production stack: Next.js + Supabase (Postgres, pgvector, RLS, Edge Functions) + Vercel.
- RAG-powered assistant over a legal knowledge base (pgvector embeddings).
- Dual-LLM (Claude + Qwen) deliberation for review classification — the same pattern the
  candidate reused and inverted to build TruReview.
- Agentic task queue with human-in-the-loop approval before anything is sent to a landlord/PM.
- Building-scoring engine (People's Score) over multiple live public sources; shadow-PBR
  detection across condo registries.

This is a shipped, operating platform, not a slide. It substantiates the candidate's
"solo technical founder, production in ~31 days" claim and the specific subsystems named on
the résumé (RAG, dual-LLM deliberation, human-in-the-loop agentic pipeline).
