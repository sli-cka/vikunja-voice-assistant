#!/usr/bin/env python3
"""Verify that all translation JSON files share identical key structure.

Usage: python scripts/check_translations.py
Exits non-zero if any file is missing or has extra keys.
"""

from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Any, Dict

TRANSLATION_DIR = (
    Path(__file__).resolve().parent.parent
    / "custom_components"
    / "vikunja_voice_assistant"
    / "translations"
)


def flatten(d: Dict[str, Any], prefix: str = ""):
    for k, v in d.items():
        new_prefix = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            yield from flatten(v, new_prefix)
        else:
            yield new_prefix


def main():
    files = [
        f
        for f in sorted(TRANSLATION_DIR.glob("*.json"))
        if f.name != "relative_phrases.json"
    ]
    if not files:
        print("No translation files found.")
        return 1
    base = None
    base_keys = set()
    problems = False
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        keys = set(flatten(data))
        if base is None:
            base = f.name
            base_keys = keys
            continue
        missing = base_keys - keys
        extra = keys - base_keys
        if missing or extra:
            problems = True
            if missing:
                print(f"[MISSING] {f.name}: {sorted(missing)}")
            if extra:
                print(f"[EXTRA]   {f.name}: {sorted(extra)}")
    if problems:
        print("Translation key mismatch detected.")
        return 2
    print(
        f"All translation files share identical key set ({len(base_keys)} keys) relative to {base}."
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
