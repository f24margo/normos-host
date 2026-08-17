"""
NKS-014 §5.4 — triage реєстру дієслів і OOV-черги.
Джерело правди реєстру: packages/msu_ua/data/norm_verbs_uk.json
OOV: data/oov_queue.json
Лише читання/запис JSON. Без логіки analyze.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from django.conf import settings

TRANSITION_TYPES = (
    "create",
    "procedure",
    "terminate",
    "delegate",
    "control",
    "state_change",
)


def _base() -> Path:
    return Path(settings.BASE_DIR)


def registry_path() -> Path:
    return _base() / "packages" / "msu_ua" / "data" / "norm_verbs_uk.json"


def oov_queue_path() -> Path:
    return _base() / "data" / "oov_queue.json"


def _load_registry() -> dict[str, Any]:
    path = registry_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("verbs"), list):
        raise ValueError("Invalid registry structure")
    return data


def _save_registry(data: dict[str, Any]) -> None:
    data["total"] = len(data.get("verbs") or [])
    data["last_updated"] = date.today().isoformat()
    path = registry_path()
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _load_oov() -> dict[str, Any]:
    path = oov_queue_path()
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _save_oov(data: dict[str, Any]) -> None:
    oov_queue_path().write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def list_verbs(status_filter: str | None = "needs_review") -> list[dict[str, Any]]:
    data = _load_registry()
    out = []
    for v in data["verbs"]:
        if not isinstance(v, dict):
            continue
        st = v.get("transition_type_status") or "default"
        if status_filter and status_filter != "all" and st != status_filter:
            continue
        out.append({
            "id": v.get("id"),
            "lemma": v.get("lemma"),
            "forms": v.get("forms") or [],
            "modality": v.get("modality"),
            "transition_type": v.get("transition_type"),
            "transition_type_status": st,
            "typical_agents": v.get("typical_agents") or [],
            "status": v.get("status"),
        })
    out.sort(key=lambda x: (x.get("lemma") or ""))
    return out


def confirm_transition(
    verb_id: str,
    transition_type: str | None = None,
) -> dict[str, Any]:
    if transition_type is not None and transition_type not in TRANSITION_TYPES:
        raise ValueError(f"Invalid transition_type: {transition_type}")

    data = _load_registry()
    found = None
    for v in data["verbs"]:
        if isinstance(v, dict) and v.get("id") == verb_id:
            found = v
            break
    if not found:
        raise KeyError(f"Verb not found: {verb_id}")

    if transition_type is not None:
        found["transition_type"] = transition_type
    found["transition_type_status"] = "reviewed"
    _save_registry(data)
    return {
        "id": found.get("id"),
        "lemma": found.get("lemma"),
        "transition_type": found.get("transition_type"),
        "transition_type_status": found.get("transition_type_status"),
    }


def list_oov_queue(pending_only: bool = True) -> list[dict[str, Any]]:
    raw = _load_oov()
    items = []
    for key, entry in raw.items():
        if not isinstance(entry, dict):
            continue
        disp = entry.get("disposition") or "pending"
        if pending_only and disp != "pending":
            continue
        items.append({
            "key": key,
            "lemma": entry.get("lemma") or key,
            "type": entry.get("type") or "lemma",
            "count": entry.get("count") or 0,
            "sources": entry.get("sources") or [],
            "disposition": disp,
        })
    items.sort(key=lambda x: (-(x["count"] or 0), x["lemma"]))
    return items


def oov_reject(key: str) -> dict[str, Any]:
    data = _load_oov()
    if key not in data:
        raise KeyError(f"OOV key not found: {key}")
    data[key]["disposition"] = "rejected"
    _save_oov(data)
    return {"key": key, "disposition": "rejected"}


def oov_accept_lemma(key: str) -> dict[str, Any]:
    oov = _load_oov()
    if key not in oov:
        raise KeyError(f"OOV key not found: {key}")
    entry = oov[key]
    lemma = (entry.get("lemma") or key).strip().lower()

    reg = _load_registry()
    for v in reg["verbs"]:
        if isinstance(v, dict) and (v.get("lemma") or "").lower() == lemma:
            oov[key]["disposition"] = "accepted_lemma"
            _save_oov(oov)
            return {
                "key": key,
                "disposition": "accepted_lemma",
                "verb_id": v.get("id"),
                "note": "lemma already in registry",
            }

    max_n = 0
    for v in reg["verbs"]:
        if not isinstance(v, dict):
            continue
        vid = v.get("id") or ""
        if vid.startswith("V") and vid[1:].isdigit():
            max_n = max(max_n, int(vid[1:]))
    new_id = f"V{max_n + 1:03d}"

    new_verb = {
        "id": new_id,
        "lemma": lemma,
        "forms": [lemma],
        "modality": "OBL",
        "transition_type": "state_change",
        "transition_type_status": "needs_review",
        "typical_agents": [],
        "status": "draft",
    }
    reg["verbs"].append(new_verb)
    _save_registry(reg)

    oov[key]["disposition"] = "accepted_lemma"
    _save_oov(oov)

    return {
        "key": key,
        "disposition": "accepted_lemma",
        "verb_id": new_id,
        "lemma": lemma,
    }


def oov_accept_form(key: str, target_lemma: str) -> dict[str, Any]:
    oov = _load_oov()
    if key not in oov:
        raise KeyError(f"OOV key not found: {key}")
    form = (oov[key].get("lemma") or key).strip().lower()
    target = target_lemma.strip().lower()

    reg = _load_registry()
    found = None
    for v in reg["verbs"]:
        if isinstance(v, dict) and (v.get("lemma") or "").lower() == target:
            found = v
            break
    if not found:
        raise KeyError(f"Target lemma not found: {target_lemma}")

    forms = list(found.get("forms") or [])
    if form not in forms:
        forms.append(form)
        found["forms"] = forms
        _save_registry(reg)

    oov[key]["disposition"] = "accepted_form"
    _save_oov(oov)
    return {
        "key": key,
        "disposition": "accepted_form",
        "verb_id": found.get("id"),
        "lemma": found.get("lemma"),
        "form": form,
    }