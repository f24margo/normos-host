def generate_recommendations(triplets: list) -> list:
    """
    Анализирует сформированные триплеты и генерирует юридические подсказки и предупреждения:
    1. Обязательство (OBL) без указания конкретного субъекта.
    2. Процедурные зависимости (depends_on) от других карточек МСУ.
    """
    recommendations = []

    for idx, t in enumerate(triplets):
        # 1. Проверка: Императивный обязанность без явно названного субъекта
        if t.get("modality") == "OBL" and not t.get("subject"):
            recommendations.append({
                "type": "warning",
                "code": "MISSING_SUBJECT_OBLIGATION",
                "triplet_index": idx,
                "title": "Обов'язок без визначеного суб'єкта",
                "message": f"Предписано обов'язок («{t.get('action')}»), але суб'єкт виконання не вказаний в клаузі. Рекомендується уточнити відповідальну роль."
            })

        # 2. Проверка: Наличие процедурных условий и зависимостей
        deps = t.get("depends_on", [])
        if deps:
            recommendations.append({
                "type": "info",
                "code": "PROCEDURAL_DEPENDENCY",
                "triplet_index": idx,
                "title": "Процедурна залежність",
                "message": f"Реалізація дії «{t.get('action')}» вимагає попереднього виконання норм/процедур: {', '.join(deps)}."
            })

    return recommendations