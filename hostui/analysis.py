"""Тонкий міст: Host → NormOS core (lab-draft)."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Шлях до lab-draft (за потреби змініть)
LAB_DRAFT_ROOT = Path("/Users/nikolayfilatov/normos-lab-draft")


def _ensure_lab_on_path() -> None:
    root = str(LAB_DRAFT_ROOT.resolve())
    if root not in sys.path:
        sys.path.insert(0, root)


def analyze_text(text: str) -> dict[str, Any]:
    """
    Повертає словник для шаблону кабінету.
    Не прокидає в UI внутрішні терміни ядра без потреби.
    """
    text = (text or "").strip()
    if not text:
        return {
            "ok": False,
            "headline": "Порожній текст",
            "details": "Вставте текст документа.",
            "raw": None,
        }

    _ensure_lab_on_path()
    try:
        from core.inference import InferenceEngine
    except ImportError as e:
        return {
            "ok": False,
            "headline": "Ядро аналізу недоступне",
            "details": f"Не вдалося імпортувати core: {e}",
            "raw": None,
        }

    try:
        engine = InferenceEngine()
        r = engine.infer(text)
    except Exception as e:
        return {
            "ok": False,
            "headline": "Помилка під час аналізу",
            "details": str(e),
            "raw": None,
        }

    headline = r.get("result") or "Результат не визначено"
    deciding = r.get("deciding_verb")
    modality = r.get("modality")
    oov = r.get("oov")
    verbs = r.get("verbs_found") or []

    # Короткі деталі простими словами
    lines = []
    if deciding:
        lines.append(f"Ключова дія в тексті: {deciding}")
    if modality:
        mode_uk = {
            "OBL": "обов’язок",
            "PERM": "дозвіл",
            "PROH": "заборона",
            "POW": "повноваження",
        }.get(str(modality), str(modality))
        lines.append(f"Режим (орієнтовно): {mode_uk}")
    if oov:
        lines.append("Типові дії з довідника в цьому тексті не розпізнано.")
    if isinstance(verbs, list) and verbs:
        # verbs можуть бути str або dict
        labels = []
        for v in verbs[:12]:
            if isinstance(v, dict):
                labels.append(v.get("lemma") or v.get("base_form") or str(v))
            else:
                labels.append(str(v))
        if labels:
            lines.append("Знайдені дії: " + ", ".join(labels))

    return {
        "ok": True,
        "headline": headline,
        "details": "\n".join(lines) if lines else "",
        "char_count": len(text),
        "raw": r,
    }