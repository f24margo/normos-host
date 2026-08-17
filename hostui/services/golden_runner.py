"""
NKS-014 §5.2 — тонкая обгортка Golden Tests.
Жодної власної нормалізації/матчингу: лише analyze_document_pipeline + порівняння expect.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from django.conf import settings

from hostui.services.markup import analyze_document_pipeline


def _cases_path() -> Path:
    return Path(settings.BASE_DIR) / "tests" / "golden" / "cases.yaml"


def load_cases() -> list[dict[str, Any]]:
    path = _cases_path()
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    cases = data.get("cases") or []
    return cases if isinstance(cases, list) else []


def _card_ids_from_triplet(t: dict) -> list[str]:
    ids: list[str] = []
    for c in t.get("cards") or []:
        if isinstance(c, str):
            ids.append(c)
        elif isinstance(c, dict) and c.get("id"):
            ids.append(str(c["id"]))
    return ids


def _check_case(case: dict[str, Any], result: dict[str, Any]) -> tuple[bool, list[str]]:
    """Повертає (passed, list of diff messages)."""
    diffs: list[str] = []
    expect = case.get("expect") or {}
    triplets = result.get("triplets") or []
    n = len(triplets)

    if "min_triplets" in expect and n < int(expect["min_triplets"]):
        diffs.append(f"min_triplets: expected >= {expect['min_triplets']}, got {n}")
    if "max_triplets" in expect and n > int(expect["max_triplets"]):
        diffs.append(f"max_triplets: expected <= {expect['max_triplets']}, got {n}")

    actions = [(t.get("action") or "") for t in triplets]
    if expect.get("actions_any"):
        wanted = list(expect["actions_any"])
        if not any(any(w in a for a in actions) for w in wanted):
            diffs.append(f"actions_any: none of {wanted} in {actions}")

    all_cards: list[str] = []
    for t in triplets:
        all_cards.extend(_card_ids_from_triplet(t))
    if expect.get("card_ids_any"):
        wanted = set(expect["card_ids_any"])
        if not wanted.intersection(all_cards):
            diffs.append(f"card_ids_any: expected any of {sorted(wanted)}, got {all_cards}")

    return (len(diffs) == 0, diffs)


def run_golden_tests() -> dict[str, Any]:
    cases = load_cases()
    results = []
    passed = 0
    failed = 0

    for case in cases:
        cid = case.get("id") or "?"
        text = case.get("text") or ""
        try:
            raw = analyze_document_pipeline(text)
            ok, diffs = _check_case(case, raw)
        except Exception as e:
            ok, diffs = False, [f"exception: {e}"]
            raw = {}

        if ok:
            passed += 1
        else:
            failed += 1

        results.append({
            "id": cid,
            "description": case.get("description") or "",
            "passed": ok,
            "diffs": diffs,
            "triplet_count": len(raw.get("triplets") or []),
        })

    return {
        "total": len(cases),
        "passed": passed,
        "failed": failed,
        "cases": results,
        "cases_path": str(_cases_path().relative_to(Path(settings.BASE_DIR))),
    }