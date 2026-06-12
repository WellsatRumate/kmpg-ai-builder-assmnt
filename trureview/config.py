"""Central config. One place to point at your model and tune run behaviour."""

import os
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent
REPO_DIR = PKG_DIR.parent
PROMPTS_DIR = PKG_DIR / "prompts" if (PKG_DIR / "prompts").exists() else REPO_DIR / "prompts"
MOCK_PAGES_DIR = REPO_DIR / "data" / "mock_pages"
OUTPUTS_DIR = REPO_DIR / "outputs"

# Set TRUREVIEW_MODEL to whatever your Anthropic account exposes.
DEFAULT_MODEL = os.getenv("TRUREVIEW_MODEL", "claude-sonnet-4-5")
MAX_TOKENS = int(os.getenv("TRUREVIEW_MAX_TOKENS", "1500"))

# Protected categories the redaction layer must strip from extracted evidence.
# This list is intentionally explicit and auditable.
PROTECTED_CATEGORIES = [
    "age", "date of birth", "race", "ethnicity", "national origin",
    "religion", "health", "disability", "pregnancy", "family status",
    "marital status", "sexual orientation", "gender identity", "political affiliation",
]
