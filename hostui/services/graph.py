def build_norm_graph(triplets: list) -> dict:
    """
    Формирует структуру узлов и рёбер для Vis.js:
    - O(n) Hub-топология для субъектов.
    - Исключение заглушки 'Загальна норма' из связей.
    - Очистка от incomplete-триплетов.
    """
    nodes = []
    edges = []
    subject_hubs = set()

    for idx, t in enumerate(triplets):
        # Пропускаем неполные триплеты (без глагола действия)
        if t.get("incomplete"):
            continue

        norm_id = f"norm_{idx+1}"
        action_label = t.get("action", "дія")
        mod = t.get("modality", "NORM")
        
        # Узел нормы/триплета
        nodes.append({
            "id": norm_id,
            "label": f"[{mod}] {action_label}",
            "group": mod,
            "shape": "box"
        })

        # 1. Процедурные связи depends_on (Критический приоритет)
        for dep in t.get("depends_on", []):
            edges.append({
                "from": dep,
                "to": norm_id,
                "label": "залежить від",
                "color": {"color": "#ef4444"},
                "arrows": "to",
                "type": "depends_on"
            })

        # 2. Hub-топология субъектов O(n)
        subj = t.get("subject")
        if subj and subj != "Загальна норма":
            hub_id = f"hub_{subj}"
            if hub_id not in subject_hubs:
                subject_hubs.add(hub_id)
                nodes.append({
                    "id": hub_id,
                    "label": f"🏛️ {subj}",
                    "group": "SUBJECT_HUB",
                    "shape": "ellipse",
                    "color": "#818cf8"
                })
            
            edges.append({
                "from": hub_id,
                "to": norm_id,
                "type": "has_norm",
                "dashes": True,
                "color": {"color": "#cbd5e1"}
            })

    return {"nodes": nodes, "edges": edges}

# Алиас для обратной совместимости
build_graph_data = build_norm_graph