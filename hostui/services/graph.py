import logging

logger = logging.getLogger(__name__)

# === БЛОК 1: Чистый генератор графа зависимостей ===
def build_dependency_graph(triplets: list, roles_in_doc: list = None) -> dict:
    """
    Строит граф узлов и связей исключительно на основе атрибутов триплетов.
    Не содержит зашитых списков ролей и текстового поиска.
    """
    nodes = []
    edges = []
    added_nodes = set()

    if not triplets:
        return {"nodes": [], "edges": []}

    def ensure_node(node_id: str, label: str, node_type: str = "action"):
        """Динамически создает узел, если он еще не добавлен."""
        if node_id not in added_nodes:
            nodes.append({
                "id": node_id,
                "label": label,
                "type": node_type
            })
            added_nodes.add(node_id)

    # === БЛОК 2: Построение узлов и связей ===
    for idx, t in enumerate(triplets):
        node_id = f"node_{idx}"
        action = t.get("action", "дія")
        subj = t.get("subject") or "Загальна норма"
        is_contextual = t.get("is_contextual", False)

        # 1. Узел самого действия
        ensure_node(node_id, action, node_type="action")

        # 2. Связь с субъектом (если субъект известен)
        if subj != "Загальна норма":
            hub_id = f"hub_{subj.lower().strip()}"
            ensure_node(hub_id, subj.capitalize(), node_type="hub")

            # Выбор стиля связи на основе флага из экстрактора
            edges.append({
                "from": hub_id,
                "to": node_id,
                "source": hub_id,
                "target": node_id,
                "type": "context_subject" if is_contextual else "SUBJECT_HUB",
                "style": "dashed" if is_contextual else "solid",
                "label": "контекст" if is_contextual else "суб'єкт"
            })

        # 3. Связи с карточками норм (depends_on)
        for dep_card_id in t.get("depends_on", []):
            card_node_id = f"card_{dep_card_id}"
            ensure_node(card_node_id, f"Карточка {dep_card_id}", node_type="card")

            edges.append({
                "from": node_id,
                "to": card_node_id,
                "source": node_id,
                "target": card_node_id,
                "type": "depends_on",
                "style": "dotted",
                "label": "залежить"
            })

    return {"nodes": nodes, "edges": edges}


# Алиас для обратной совместимости
build_norm_graph = build_dependency_graph