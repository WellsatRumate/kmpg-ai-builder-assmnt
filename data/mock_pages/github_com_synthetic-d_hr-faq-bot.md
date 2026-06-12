# hr-faq-bot
Internal HR FAQ assistant. Textbook RAG pipeline: PDF loader -> recursive text
splitter -> embeddings -> vector store -> top-k retriever -> LLM answer with source
citations. Closely follows the framework's reference template; very few deviations.
Has a confidence-threshold fallback that routes to "ask HR" when retrieval score is
low. ~120 commits, mostly config and prompt tweaks. README is clear and honest. No
eval harness beyond manual spot-checks. Works reliably — and there is nothing here a
competent developer would not have built the same way from the standard tutorial.
