import os
import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = "Збирає швидкі індекси lookup (by_verb, by_agent, by_source) з JSON-карток msu_ua"

    def handle(self, *args, **options):
        base_dir = Path(settings.BASE_DIR)
        pkg_dir = base_dir / "packages" / "msu_ua"
        cards_dir = pkg_dir / "cards"
        sources_dir = pkg_dir / "sources"
        index_dir = pkg_dir / "index"

        # Створюємо директорію index, якщо її немає
        index_dir.mkdir(parents=True, exist_ok=True)

        by_verb = {}
        by_agent = {}
        by_source = {}

        card_files = list(cards_dir.glob("*.json"))
        self.stdout.write(f"Знайдено карточок для індексації: {len(card_files)}")

        indexed_count = 0

        for card_path in card_files:
            try:
                with open(card_path, "r", encoding="utf-8") as f:
                    card = json.load(f)
            except Exception as e:
                self.stderr.write(f"Помилка читання {card_path.name}: {e}")
                continue

            card_id = card.get("id")
            if not card_id:
                continue

            status = card.get("status", "draft")
            # Індексуємо всі картки або тільки active/draft за потребою
            
            # 1. Індексація за дієсловами (verbs)
            for verb in card.get("verbs", []):
                verb_lower = verb.strip().lower()
                if verb_lower not in by_verb:
                    by_verb[verb_lower] = []
                if card_id not in by_verb[verb_lower]:
                    by_verb[verb_lower].append(card_id)

            # 2. Індексація за суб'єктами (agents)
            for agent in card.get("agents", []):
                agent_lower = agent.strip().lower()
                if agent_lower not in by_agent:
                    by_agent[agent_lower] = []
                if card_id not in by_agent[agent_lower]:
                    by_agent[agent_lower].append(card_id)

            # 3. Індексація за джерелами (sources)
            for src in card.get("sources", []):
                src_id = src.get("source_id")
                if src_id:
                    if src_id not in by_source:
                        by_source[src_id] = []
                    if card_id not in by_source[src_id]:
                        by_source[src_id].append(card_id)

            indexed_count += 1

        # Запис згенерованих індексів на диск
        with open(index_dir / "by_verb.json", "w", encoding="utf-8") as f:
            json.dump(by_verb, f, ensure_ascii=False, indent=2)

        with open(index_dir / "by_agent.json", "w", encoding="utf-8") as f:
            json.dump(by_agent, f, ensure_ascii=False, indent=2)

        with open(index_dir / "by_source.json", "w", encoding="utf-8") as f:
            json.dump(by_source, f, ensure_ascii=False, indent=2)

        # Оновлюємо package.json
        pkg_json_path = pkg_dir / "package.json"
        if pkg_json_path.exists():
            with open(pkg_json_path, "r", encoding="utf-8") as f:
                pkg_data = json.load(f)
            pkg_data["card_count"] = indexed_count
            with open(pkg_json_path, "w", encoding="utf-8") as f:
                json.dump(pkg_data, f, ensure_ascii=False, indent=2)

        self.stdout.write(
            self.style.SUCCESS(
                f"Успішно проіндексовано {indexed_count} карток!\n"
                f" - Ключів дієслів: {len(by_verb)}\n"
                f" - Ключів суб'єктів: {len(by_agent)}\n"
                f" - Збережено у {index_dir}"
            )
        )