import json
import re
from pathlib import Path
from django.conf import settings

# Кэш индексов в RAM
INDEX_CACHE = {}

def load_indexes():
    """Загружает индексы пакета msu_ua в память при первом обращении."""
    if INDEX_CACHE:
        return INDEX_CACHE

    pkg_index_dir = Path(settings.BASE_DIR) / "packages" / "msu_ua" / "index"
    
    by_verb_file = pkg_index_dir / "by_verb.json"
    by_agent_file = pkg_index_dir / "by_agent.json"

    by_verb = json.load(open(by_verb_file, "r", encoding="utf-8")) if by_verb_file.exists() else {}
    by_agent = json.load(open(by_agent_file, "r", encoding="utf-8")) if by_agent_file.exists() else {}

    INDEX_CACHE["by_verb"] = by_verb
    INDEX_CACHE["by_agent"] = by_agent
    return INDEX_CACHE


def analyze_document(text: str, layers: list = None) -> dict:
    if layers is None:
        layers = ["verbs", "modality", "roles", "msu"]

    indexes = load_indexes()
    by_verb = indexes.get("by_verb", {})
    by_agent = indexes.get("by_agent", {})

    spans = []

    # 1. Поиск совпадений по глаголам и карточкам MSU
    if "verbs" in layers or "msu" in layers:
        for verb, card_ids in by_verb.items():
            pattern = re.compile(r'\b' + re.escape(verb) + r'\b', re.IGNORECASE)
            for match in pattern.finditer(text):
                start, end = match.span()

                if "verbs" in layers:
                    spans.append({
                        "start": start,
                        "end": end,
                        "layer": "verbs",
                        "class": "layer-verb",
                        "label": f"Дія: {match.group()}"
                    })

                if "msu" in layers:
                    for cid in card_ids:
                        spans.append({
                            "start": start,
                            "end": end,
                            "layer": "msu",
                            "class": "layer-msu",
                            "card_id": cid,
                            "label": f"Норма {cid}"
                        })

    spans.sort(key=lambda x: x["start"])

    # Сохраняем и существующие поля ответа, и новые spans
    return {
        "text": text,
        "active_layers": layers,
        "spans": spans,
        "matched_cards_count": len(set(s.get("card_id") for s in spans if "card_id" in s)),
        "status": "success"
    }