from typing import Any, Dict, Optional

DISCLAIMER = "Аналіз згенеровано автоматично. Результат має інформаційний характер і не є офіційним юридичним висновком."

def analyze_document(text: str, *, user: Optional[Any] = None, tenant: Optional[Any] = None) -> Dict[str, Any]:
    """
    Єдиний фасад NormOS.
    Штатно імпортує InferenceEngine з установленого пакета normos-lab-demo.
    """
    text = (text or "").strip()
    if not text:
        return {
            "ok": False,
            "verdict": None,
            "warnings": ["Текст для аналізу відсутній. Вставте текст документа."],
            "hints": [],
            "cards": [],
            "meta": {"char_count": 0, "core_available": False},
            "disclaimer": DISCLAIMER,
        }

    try:
        from core.inference import InferenceEngine
    except ImportError as e:
        return {
            "ok": False,
            "verdict": None,
            "warnings": [f"Ядро аналізу недоступне: {e}"],
            "hints": [],
            "cards": [],
            "meta": {"char_count": len(text), "core_available": False},
            "disclaimer": DISCLAIMER,
        }

    try:
        engine = InferenceEngine()
        r = engine.infer(text)
    except Exception as e:
        return {
            "ok": False,
            "verdict": None,
            "warnings": [f"Помилка під час аналізу: {str(e)}"],
            "hints": [],
            "cards": [],
            "meta": {"char_count": len(text), "core_available": True},
            "disclaimer": DISCLAIMER,
        }

    headline = r.get("result") or "Результат не визначено"
    deciding = r.get("deciding_verb")
    modality = r.get("modality")
    oov = r.get("oov")
    verbs_raw = r.get("verbs_found") or []

    verbs_found = []
    if isinstance(verbs_raw, list):
        for v in verbs_raw[:12]:
            if isinstance(v, dict):
                verbs_found.append(v.get("lemma") or v.get("base_form") or str(v))
            else:
                verbs_found.append(str(v))

    mode_uk = {
        "OBL": "обов’язок (OBL)",
        "PERM": "дозвіл (PERM)",
        "PROH": "заборона (PROH)",
        "POW": "повноваження (POW)",
    }.get(str(modality), str(modality)) if modality else None

    hints = []
    if oov:
        hints.append({"text": "Типові дії з довідника в цьому тексті не розпізнано (OOV).", "level": "warning"})
    if verbs_found:
        hints.append({"text": f"Знайдені дії в тексті: {', '.join(verbs_found)}", "level": "info"})

    return {
        "ok": True,
        "verdict": {
            "headline": headline,
            "deciding_verb": deciding,
            "modality": modality,
            "modality_text": mode_uk,
            "verbs_found": verbs_found,
        },
        "warnings": [],
        "hints": hints[:3],
        "cards": [],
        "meta": {
            "char_count": len(text),
            "catalog_version": "msu_ua@0.1.0",
            "core_available": True,
        },
        "disclaimer": DISCLAIMER,
        "raw": r,
    }
