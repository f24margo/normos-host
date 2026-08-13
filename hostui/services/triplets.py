from hostui.services.roles import select_clause_subject

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
    Собирает триплеты ⟨Субъект, Модальность, Действие⟩ для отдельной клаузы:
    - Выбирает субъект с приоритетом именительного падежа.
    - Выполняет 1-к-N декомпозицию для однородных сказуемых.
    - Извлекает связи depends_on из привязанных карточек МСУ.
    - Фиксирует безличные предписания (subject: null).
    """
    # 1. Извлекаем роли, находящиеся в пределах текущей клаузы
    clause_roles = [
        r for r in all_role_matches 
        if clause_start <= r["start"] and r["end"] <= clause_end
    ]
    
    # 2. Выбираем субъект (Nominative Priority)
    selected_subject = select_clause_subject(clause_roles)

    # 3. Извлекаем действия (глаголы из реестра), попавшие в клаузу
    clause_verbs = [
        v for v in matched_verbs_list 
        if clause_start <= v["start"] and v["end"] <= clause_end
    ]

    clause_triplets = []

    if clause_verbs:
        # Декомпозиция 1-к-N: создаем отдельный триплет под каждое действие
        for v_item in clause_verbs:
            depends_on_list = []
            for cid in v_item["card_ids"]:
                card_data = cards_db.get(cid, {})
                if "depends_on" in card_data:
                    depends_on_list.extend(card_data["depends_on"])

            clause_triplets.append({
                "subject": selected_subject,  # None = subject: null (Загальна норма)
                "modality": final_modality_cat,
                "action": v_item["text"],
                "verb_lemma": v_item["verb"],
                "modality_source": modality_source,
                "marker": applied_marker,
                "cards": v_item["card_ids"],
                "depends_on": list(set(depends_on_list)),
                "clause_text": clause
            })
            
    elif found_markers:
        # Безглагольная клауза с явно выраженным модальным маркером
        clause_triplets.append({
            "subject": selected_subject,
            "modality": final_modality_cat,
            "action": "дію не вказано",
            "verb_lemma": None,
            "modality_source": modality_source,
            "marker": applied_marker,
            "cards": [],
            "depends_on": [],
            "clause_text": clause
        })

    return clause_triplets