"""
NKS-014 §5.1 — збір статусу системи для Research Console.
Лише читання файлів / git. Без логіки аналізу тексту.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from django.conf import settings


def _base_dir() -> Path:
    return Path(settings.BASE_DIR)


def _file_sha256(path: Path, nbytes: int = 12) -> str:
    """Короткий hash вмісту файлу (для бейджа, не крипто-аудит)."""
    try:
        h = hashlib.sha256(path.read_bytes()).hexdigest()
        return h[:nbytes]
    except OSError:
        return "unavailable"


def _git_commit_short() -> str:
    """HEAD short hash; на проді без .git → 'unknown'."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(_base_dir()),
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "unknown"


def _load_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def get_registry_status() -> dict[str, Any]:
    """
    Джерело правди: packages/msu_ua/data/norm_verbs_uk.json (v0.3.0+).
    """
    path = _base_dir() / "packages" / "msu_ua" / "data" / "norm_verbs_uk.json"
    data = _load_json(path)
    if not isinstance(data, dict):
        return {
            "ok": False,
            "path": str(path),
            "version": None,
            "lemmas": 0,
            "needs_review": 0,
            "content_hash": None,
            "error": "registry file missing or invalid JSON",
        }

    verbs = data.get("verbs") or []
    if not isinstance(verbs, list):
        verbs = []

    needs_review = 0
    for v in verbs:
        if isinstance(v, dict) and v.get("transition_type_status") == "needs_review":
            needs_review += 1

    total = data.get("total")
    if not isinstance(total, int):
        total = len(verbs)

    return {
        "ok": True,
        "path": str(path.relative_to(_base_dir())),
        "version": data.get("version"),
        "lemmas": total,
        "needs_review": needs_review,
        "content_hash": _file_sha256(path),
        "error": None,
    }


def get_catalog_status() -> dict[str, Any]:
    """Картки packages/msu_ua/cards + version з package.json."""
    pkg_dir = _base_dir() / "packages" / "msu_ua"
    cards_dir = pkg_dir / "cards"
    package_json = pkg_dir / "package.json"

    pkg_version = None
    pkg = _load_json(package_json)
    if isinstance(pkg, dict):
        pkg_version = pkg.get("version")

    draft = 0
    active = 0
    other = 0
    card_files: list[Path] = []
    if cards_dir.is_dir():
        card_files = sorted(cards_dir.glob("N*.json"))
        for f in card_files:
            c = _load_json(f)
            if not isinstance(c, dict):
                other += 1
                continue
            st = (c.get("status") or "").lower()
            if st == "draft":
                draft += 1
            elif st == "active":
                active += 1
            else:
                other += 1

    return {
        "ok": cards_dir.is_dir(),
        "name": "msu_ua",
        "version": pkg_version,
        "cards": len(card_files),
        "draft": draft,
        "active": active,
        "other_status": other,
        "error": None if cards_dir.is_dir() else "cards directory missing",
    }


def get_host_status() -> dict[str, Any]:
    return {
        "commit": _git_commit_short(),
    }


def get_system_status() -> dict[str, Any]:
    """Повний зліпок для шапки Research Console (5.1)."""
    return {
        "registry": get_registry_status(),
        "catalog": get_catalog_status(),
        "host": get_host_status(),
    }
    