"""
Evidence enrichment — the consent boundary, made structural.

THE GOVERNANCE INVARIANT OF THIS WHOLE SYSTEM:
    Enrichment acts ONLY on links the candidate explicitly provided on their
    application. There is no function anywhere in this codebase that discovers,
    searches for, or goes looking for sources about a person. The capability does
    not exist here, by construction. That absence is the design.

Lineage note: these agents began life in BYAMN as aggressive outreach recon. The
exact same extraction muscle is reused here, but the SOURCING TRIGGER is inverted:
in outreach, the risk sat on the sender (me); in evaluation, the risk sits on the
candidate, so discovery is removed and only consented links are deep-dived.

In demo/offline mode, "fetching" a provided link reads a local mock page so the
build is fully runnable with no live network calls. The real fetch is a TODO
behind the SAME interface (fetch_provided), so swapping mock->real never widens
the consent boundary.
"""

from __future__ import annotations

import json
from pathlib import Path

from .config import MOCK_PAGES_DIR
from .llm import load_prompt
from .redaction import scrub, categories_reminder
from .schemas import Application, EvidenceBundle, EvidenceItem, ProvidedLink


def _slug(url: str) -> str:
    return (
        url.replace("https://", "").replace("http://", "")
        .replace("/", "_").replace(".", "_").rstrip("_")
    )


def fetch_provided(link: ProvidedLink, application: Application) -> str:
    """Fetch the content of a CANDIDATE-PROVIDED link only.

    Hard guard: refuse anything not present in application.provided_links. This makes
    it impossible for a caller to smuggle in a discovered URL.
    """
    if link.url not in {l.url for l in application.provided_links}:
        raise PermissionError(
            f"Refusing to fetch '{link.url}': not a candidate-provided link. "
            f"Enrichment is consent-bounded; there is no discovery path."
        )
    # DEMO MODE: read local mock page. REAL MODE TODO: replace this body with a
    # fetch of link.url behind the identical signature. Do not add a search step.
    mock = MOCK_PAGES_DIR / f"{_slug(link.url)}.md"
    if mock.exists():
        return mock.read_text(encoding="utf-8")
    return f"[no mock page for {link.url}; provide one in data/mock_pages/]"


def enrich(application: Application, llm) -> EvidenceBundle:
    """Build an EvidenceBundle from resume text + provided links ONLY."""
    from concurrent.futures import ThreadPoolExecutor, as_completed as _as_completed

    extraction_prompt = load_prompt("extraction.md").replace(
        "{{PROTECTED_CATEGORIES}}", categories_reminder()
    )

    bundle = EvidenceBundle(candidate_id=application.candidate_id)

    # 1) Resume itself is consented evidence.
    sources: list[tuple[str, str | None, str]] = [
        ("resume", None, application.resume_text)
    ]
    # 2) Each candidate-provided link.
    for link in application.provided_links:
        content = fetch_provided(link, application)
        sources.append((f"{link.label} ({link.kind})", link.url, content))

    def extract_one(args):
        idx, source_label, source_url, raw = args
        user = (
            f"SOURCE LABEL: {source_label}\nSOURCE URL: {source_url or 'n/a'}\n\n"
            f"CONTENT:\n{raw}\n"
        )
        parsed = llm.complete_json(system=extraction_prompt, user=user)
        return idx, source_label, source_url, parsed

    items_by_idx: dict[int, list] = {}
    with ThreadPoolExecutor(max_workers=len(sources)) as ex:
        futures = {ex.submit(extract_one, (i, sl, su, r)): i for i, (sl, su, r) in enumerate(sources)}
        for f in _as_completed(futures):
            idx, source_label, source_url, parsed = f.result()
            items_by_idx[idx] = (source_label, source_url, parsed)

    counter = 1
    for idx in sorted(items_by_idx):
        source_label, source_url, parsed = items_by_idx[idx]
        for raw_item in parsed.get("items", []):
            signal = raw_item.get("claim_or_signal", "")
            signal, log = scrub(signal)
            bundle.items.append(
                EvidenceItem(
                    evidence_id=f"E{counter}",
                    source_label=source_label,
                    source_url=source_url,
                    claim_or_signal=signal,
                    relevance=raw_item.get("relevance", ""),
                    redacted=bool(log) or bool(raw_item.get("redacted")),
                )
            )
            bundle.redaction_log.extend(log)
            counter += 1
        bundle.redaction_log.extend(parsed.get("redaction_log", []))

    return bundle


def load_application(path: str | Path) -> Application:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return Application(**data)
