import re
from hostui.services.roles import select_clause_subject

# Расширенный набор чистых модальных маркеров (не являются самостоятельными действиями)
PURE_MODALS = {
    "може", "повинен", "зобов'язаний", "має право", "заборонено", "не може",
    "не має права", "не допускається", "не вправі", "не зобов'язаний",
    "не повинен", "не забороняється", "має право не", "забороняється", "вправі"
}


def build_clause_triplets(
    clause: str,
    clause_start: int,
    clause_end: int,
    all_role_matches: list,
    matched_verbs_list: list,
    found_markers: list,
    final_modality_cat: str,
    modality_source: str,
    applied_marker: str,
    cards_db: dict
) -> list:
    """
    Собирает триплеты ⟨Субъект, Модальность, Действие⟩ для отдельной клаузы.
    
    При отсутствии зарегистрированного глагола выполняет OOV-захват слова,
    следующего за модальным маркером.
    """
    # 1. Извлекаем роли в пределах клаузы и определяем субъект
    clause_roles = [
        r for r in all_role_matches 
        if clause_start <= r["start"] and r["end"] <= clause_end
    ]
    selected_subject = select_clause_subject(clause_roles)

    # 2. Строгая проверка границ для глаголов (исключает задвоения на стыках)
    clause_verbs = [
        v for v in matched_verbs_list 
        if clause_start <= v.get("start", -1) < clause_end
    ]

    # 3. Санитизация applied_marker (убираем строки-заглушки)
    if applied_marker in ("registry_default", "", None):
        clean_marker = None
    else:
        clean_marker = applied_marker.strip()

    clause_triplets = []

    # Вариант А: В клаузе есть самостоятельные глаголы-действия из реестра
    if clause_verbs:
        for v_item in clause_verbs:
            depends_on_list = []
            verb_default_modality = None

            for cid in v_item.get("card_ids", []):
                card_data = cards_db.get(cid, {})
                if "depends_on" in card_data:
                    depends_on_list.extend(card_data["depends_on"])
                if not verb_default_modality and "default_modality" in card_data:
                    verb_default_modality = card_data["default_modality"]

            # Если явного маркера модальности не было, подтягиваем дефолт из карточки глагола
            resolved_modality = final_modality_cat or verb_default_modality or "NORM"

            clause_triplets.append({
                "subject": selected_subject,
                "modality": resolved_modality,
                "action": v_item.get("text", v_item.get("verb")),
                "verb_lemma": v_item.get("verb"),
                "modality_source": modality_source,
                "marker": clean_marker,
                "cards": v_item.get("card_ids", []),
                "depends_on": sorted(list(set(depends_on_list))),
                "clause_text": clause,
                "incomplete": False
            })

    # Вариант Б: Глаголов из реестра нет, но есть реальный маркер
    elif clean_marker:
        marker_lower = clean_marker.lower()
        resolved_modality = final_modality_cat or "NORM"

        if marker_lower not in PURE_MODALS:
            # Маркер сам является действием (например, "здійснює", "забезпечує")
            clause_triplets.append({
                "subject": selected_subject,
                "modality": resolved_modality,
                "action": clean_marker,
                "verb_lemma": clean_marker,
                "modality_source": modality_source,
                "marker": clean_marker,
                "cards": [],
                "depends_on": [],
                "clause_text": clause,
                "incomplete": False
            })
        else:
            # Чистая модальность без известного глагола -> Ищем OOV-кандидата в тексте
            escaped_marker = re.escape(clean_marker)
            match = re.search(rf"(?i)\b{escaped_marker}\s+([а-яіїєґa-z\']+)", clause)
            oov_candidate = match.group(1).lower() if match else None

            action_label = f"[{clean_marker}] {oov_candidate} (OOV)" if oov_candidate else f"[{clean_marker}] (дія відсутня)"

            clause_triplets.append({
                "subject": selected_subject,
                "modality": resolved_modality,
                "action": action_label,
                "verb_lemma": None,
                "oov_candidate": oov_candidate,
                "modality_source": modality_source,
                "marker": clean_marker,
                "cards": [],
                "depends_on": [],
                "clause_text": clause,
                "incomplete": True
            })

    return clause_triplets


# Алиас для обратной совместимости вызовов
build_triplets_for_clause = build_clause_triplets