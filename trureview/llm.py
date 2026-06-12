"""
Single chokepoint for model calls. Everything goes through complete()/complete_json().

Two implementations:
  * AnthropicLLM  — real calls on your tokens.
  * StubLLM       — deterministic canned JSON, no network, no tokens. Lets you verify
                    the full pipeline wiring offline (`--offline`) before spending a cent.

Keeping all model access here means Codex can harden ret/timeout/retry logic in ONE
file, and Claude Code can swap models or add tool-use without touching the pipeline.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from .config import DEFAULT_MODEL, MAX_TOKENS, PROMPTS_DIR


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    return text


def extract_json(text: str):
    """Parse a JSON object/array from a model response, tolerating prose/fences."""
    cleaned = _strip_fences(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Fall back to the first {...} or [...] span.
        match = re.search(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(1))


class AnthropicLLM:
    def __init__(self, model: str = DEFAULT_MODEL):
        from anthropic import Anthropic  # imported lazily so --offline needs no SDK
        self.client = Anthropic()
        self.model = model

    def complete(self, system: str, user: str, max_tokens: int = MAX_TOKENS) -> str:
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in resp.content if block.type == "text")

    def complete_json(self, system: str, user: str, max_tokens: int = MAX_TOKENS):
        return extract_json(self.complete(system, user, max_tokens))


class StubLLM:
    """Offline stand-in. Returns structurally valid canned responses keyed by task tag.

    The task tag is passed as the first line of the system prompt: `#TASK:<tag>`.
    Good enough to prove the pipeline runs and renders; never use for real evaluation.
    """

    def complete(self, system: str, user: str, max_tokens: int = MAX_TOKENS) -> str:
        return "[offline stub text response]"

    def complete_json(self, system: str, user: str, max_tokens: int = MAX_TOKENS):
        tag = ""
        first = system.splitlines()[0] if system else ""
        if first.startswith("#TASK:"):
            tag = first.split(":", 1)[1].strip()

        if tag == "extract":
            return {
                "items": [
                    {
                        "source_label": "stub-source",
                        "claim_or_signal": "Shipped a stub project (offline placeholder).",
                        "relevance": "Demonstrates builder evidence (stub).",
                        "redacted": False,
                    }
                ],
                "redaction_log": ["[offline] no redaction performed in stub mode"],
            }
        if tag == "score":
            return {
                "score_0_5": 3.0,
                "evidence_refs": ["E1"],
                "rationale": "[offline stub] mid score against the anchor.",
            }
        if tag == "deliberate":
            return {
                "skeptic": "[offline] Evidence is thin on this facet.",
                "advocate": "[offline] But the shipped artifact counts.",
                "cites": ["E1"],
            }
        if tag == "synthesize":
            return {
                "synthesis": "[offline] Skeptic and advocate converge on conditional yes.",
                "open_questions": ["[offline] What was actually shipped vs scoped?"],
            }
        if tag == "classify":
            return {
                "corroboration_pct": 80,
                "flags": [
                    {
                        "tier": "tailored",
                        "claim": "[offline] resume mirrors the JD wording",
                        "why": "[offline stub] experience tracks; packaging echoes the JD.",
                        "what_to_verify": "[offline] confirm titles against LinkedIn.",
                    }
                ],
            }
        if tag == "gaps":
            return {"gaps": [
                {"target_claim": "[offline] led agentic transformation",
                 "gap_type": "high_polish_low_artifact"}
            ]}
        if tag == "draft":
            return {
                "question": "[offline] Walk me through the specific system you shipped.",
                "what_a_strong_answer_shows": "[offline] concrete ownership.",
            }
        return {}


def get_llm(offline: bool = False, model: Optional[str] = None):
    if offline:
        return StubLLM()
    return AnthropicLLM(model=model or DEFAULT_MODEL)


class OpenRouterLLM:
    """LLM backed by OpenRouter — drop-in replacement for AnthropicLLM."""

    def __init__(self, model: str = "qwen/qwen3.5-plus-20260420"):
        import httpx, os
        self._model = model
        self._httpx = httpx
        self._api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not self._api_key:
            raise RuntimeError("OPENROUTER_API_KEY not set in environment")

    def complete(self, system: str, user: str, max_tokens: int = MAX_TOKENS) -> str:
        resp = self._httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
            json={
                "model": self._model,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def complete_json(self, system: str, user: str, max_tokens: int = MAX_TOKENS):
        return extract_json(self.complete(system, user, max_tokens))


def get_qwen_llm(model: str = "qwen/qwen3.5-plus-20260420") -> OpenRouterLLM:
    return OpenRouterLLM(model=model)
