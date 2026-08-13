import json
from pathlib import Path
from django.conf import settings

def get_oov_queue_path() -> Path:
    data_dir = Path(settings.BASE_DIR) / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir / "oov_queue.json"

def record_oov_proposal(lemma: str, oov_type: str, source: str = "host_ui") -> dict:
    """Записывает предложение OOV в единый лог."""
    path = get_oov_queue_path()
    queue = {}
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                queue = json.load(f)
        except Exception:
            queue = {}

    entry = queue.get(lemma, {
        "lemma": lemma,
        "type": oov_type,
        "count": 0,
        "sources": [],
        "disposition": "pending"
    })
    
    entry["count"] += 1
    if source not in entry["sources"]:
        entry["sources"].append(source)
    
    queue[lemma] = entry
    with open(path, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)
        
    return entry