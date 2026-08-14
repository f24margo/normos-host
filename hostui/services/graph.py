import logging

logger = logging.getLogger(__name__)

# Блок 1: Реестр базовых субъектов-хабов (всегда в нижнем регистре)
KNOWN_HUBS = {
    "рада",
    "голова",
    "комісія",
    "депутат",
    "виконавчий комітет",
    "секретар"
}


def build_dependency_graph(triplets: list, roles_in_doc: list = None) -> dict:
    """
    Строит граф узлов и связей, включая сплошные прямые связи с хабами
    и пунктирные контекстные привязки для 'Загальна норма'.
    """
    # Блок 2: Инициализация структуры
    nodes = []
    edges = []
    node_ids = set()

    if not triplets:
        return {"nodes": [], "edges": []}

    # Блок 3: Перебор триплетов и создание узлов
    for idx, t in enumerate(triplets):
        node_id = f"node_{idx}"
        subj = t.get("subject") or "Загальна норма"
        action = t.get("action", "дія")
        modality = t.get("modality", "NEUT")
        clause_text = t.get("clause_text", "")

        nodes.append({
            "id": node_id,
            "label": action,
            "subject": subj,
            "modality": modality,
            "cards": t.get("cards", []),
            "clause": clause_text
        })
        node_ids.add(node_id)

        # Блок 4: Построение сплошных и пунктирных связей
        clean_subj = subj.lower().strip()

        # 1. Прямая связь (сплошная линия)
        if clean_subj in KNOWN_HUBS:
            edges.append({
                "source": f"hub_{clean_subj}",
                "target": node_id,
                "type": "SUBJECT_HUB",
                "style": "solid",
                "label": "суб'єкт"
            })

        # 2. Мягкая контекстная связь (пунктир) для "Загальна норма"
        elif subj == "Загальна норма" and clause_text:
            clause_lower = clause_text.lower()
            for hub in KNOWN_HUBS:
                if hub in clause_lower:
                    edges.append({
                        "source": f"hub_{hub}",
                        "target": node_id,
                        "type": "context_subject",
                        "style": "dashed",
                        "label": "контекст"
                    })

        # Блок 5: Межнормовые зависимости
        for dep_card_id in t.get("depends_on", []):
            edges.append({
                "source": node_id,
                "target": f"card_{dep_card_id}",
                "type": "depends_on",
                "style": "dotted",
                "label": "залежить"
            })

    return {"nodes": nodes, "edges": edges}
