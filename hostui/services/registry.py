import json
from pathlib import Path
from django.conf import settings

class RegistryService:
    """Сервис загрузки, кэширования и управления нормативными индексами и словарями."""
    
    def __init__(self):
        self.base_dir = Path(settings.BASE_DIR)
        self.package_dir = self.base_dir / "packages" / "msu_ua"
        self.oov_path = self.base_dir / "data" / "oov_queue.json"
        
        self.verbs_db = {}
        self.agents_db = {}
        self.cards_db = {}
        
        self.reload_all()

    def reload_all(self):
        """Загрузка всех индексов из диска в память."""
        by_verb_file = self.package_dir / "index" / "by_verb.json"
        by_agent_file = self.package_dir / "index" / "by_agent.json"
        cards_dir = self.package_dir / "cards"

        if by_verb_file.exists():
            with open(by_verb_file, "r", encoding="utf-8") as f:
                self.verbs_db = json.load(f)

        if by_agent_file.exists():
            with open(by_agent_file, "r", encoding="utf-8") as f:
                self.agents_db = json.load(f)

        # Загрузка карточек МСУ
        self.cards_db = {}
        if cards_dir.exists():
            for card_file in cards_dir.glob("*.json"):
                try:
                    with open(card_file, "r", encoding="utf-8") as f:
                        cdata = json.load(f)
                        cid = cdata.get("id") or card_file.stem
                        self.cards_db[cid] = cdata
                except Exception:
                    pass

    def get_oov_queue(self) -> dict:
        """Получение очереди OOV-кандидатов."""
        if self.oov_path.exists():
            try:
                with open(self.oov_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}