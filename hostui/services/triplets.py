import re
from hostui.services.roles import select_clause_subject

# Чистые модальные маркеры
PURE_MODALS = {
    "може", "повинен", "зобов'язаний", "має право", "заборонено", "не може",
    "не має права", "не допускається", "не вправі", "не зобов'язаний",
    "не повинен", "не забороняється", "має право не", "забороняється", "вправі"
}


def _analyze_oov_candidate(candidate_word: str, verbs_db: dict) -> dict:
    """
    Анализирует OOV-слово относительно реестра глаголов (verbs_db / by_verb.json):
    1. Инфинитив -> проверяет по симметричному Root-policy (>=6 символов) с известными леммами глаголов.
    2. Не инфинитив -> фиксирует как именную конструкцию (noun_construction).
    """
    if not candidate_word:
        return {"kind": "none", "label": "(дія відсутня)", "candidate": None}

    cand = candidate_word.lower().strip()
    is_infinitive = bool(re.search(r"(ти|тися|тись)$", cand, re.IGNORECASE))

    if not is_infinitive:
        return {
            "kind": "noun_construction",
            "label": f"[{cand}] (іменникова конструкція)",
            "candidate": cand
        }

    # Симметричная проверка по Root-policy (>=6 символов) с РЕЕСТРОМ ГЛАГОЛОВ
    cand_prefix = cand[:6] if len(cand) >= 6 else cand
    is_known_root = False

    # Извлекаем все известные леммы из verbs_db (by_verb.json)
    known_lemmas = set()
    if isinstance(verbs_db, dict):
        for k, v in verbs_db.items():
            if isinstance(v, dict) and "lemma" in v:
                known_lemmas.add(v["lemma"].lower())
            elif isinstance(k, str):
                known_lemmas.add(k.lower())

    for lemma in known_lemmas:
        lemma_prefix = lemma[:6] if len(lemma) >= 6 else lemma
        
        # Для коротких слов (< 6) — точное совпадение, для длинных — совпадение первых 6 букв
        if len(cand) < 6 or len(lemma) < 6:
            if cand == lemma:
                is_known_root = True
                break
        else:
            if cand_prefix == lemma_prefix:
                is_known_root = True
                break

    if is_known_root:
        return {
            "kind": "oov_form",
            "label": f"{cand} (OOV: нова форма)",
            "candidate": cand
        }
    else:
        return {
            "kind": "oov_lemma",
            "label": f"{cand} (OOV: нова лема)",
            "candidate": cand
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
    cards_db: dict,
    verbs_db: dict = None  # Передаём реестр глаголов by_verb.json
) -> list:
    """
    Собирает триплеты ⟨Субъект, Модальность, Действие⟩ для отдельной клаузы.
    """
    # 1. Извлекаем роли и определяем субъект
    clause_roles = [
        r for r in all_role_matches 
        if clause_start <= r["start"] and r["end"] <= clause_end
    ]
    selected_subject = select_clause_subject(clause_roles)

    # 2. Строгая проверка границ (осознанное решение: глагол принадлежит клаузе по своей стартовой позиции)
    clause_verbs = [
        v for v in matched_verbs_list 
        if clause_start <= v.get("start", -1) < clause_end
    ]

    # 3. Санитизация applied_marker
    if applied_marker in ("registry_default", "", None):
        clean_marker = None
    else:
        clean_marker = applied_marker.strip()

    clause_triplets = []

    # Вариант А: Есть самостоятельные глаголы из реестра
    if clause_verbs:
        for v_item in clause_verbs:
            depends_on_list = []
            verb_default_modality = None

            for cid in v_item.get("card_ids", []):
                card_data = cards_db.get(cid, {}) if cards_db else {}
                if "depends_on" in card_data:
                    depends_on_list.extend(card_data["depends_on"])
                if not verb_default_modality and "default_modality" in card_data:
                    verb_default_modality = card_data["default_modality"]

            # Модальность из закрытого множества {OBL, PERM, PROH} или None
            resolved_modality = final_modality_cat or verb_default_modality or None

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
                "incomplete": False,
                "oov_type": "none"
            })

    # Вариант Б: Глаголов из реестра нет, но есть маркер
    elif clean_marker:
        marker_lower = clean_marker.lower()
        resolved_modality = final_modality_cat or None

        if marker_lower not in PURE_MODALS:
            # Маркер сам является смысловым действием
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
                "incomplete": False,
                "oov_type": "none"
            })
        else:
            # Чистая модальность -> ищем инфинитив после маркера (учитывая возможные вводные вставки)
            escaped_marker = re.escape(clean_marker)
            
            # 1. Сначала ищем первый инфинитив в клаузе после маркера
            inf_match = re.search(rf"(?i)\b{escaped_marker}\b[\s\S]*?\b([а-яіїєґa-z\']+(?:ти|тися|тись))\b", clause)
            
            if inf_match:
                raw_candidate = inf_match.group(1)
            else:
                # 2. Если инфинитив не найден, берем непосредственно следующее слово (для отлова именных конструкций)
                next_word_match = re.search(rf"(?i)\b{escaped_marker}\s+([а-яіїєґa-z\']+)", clause)
                raw_candidate = next_word_match.group(1) if next_word_match else None

            # Сверяем кандидата С РЕЕСТРОМ ГЛАГОЛОВ (verbs_db)
            oov_res = _analyze_oov_candidate(raw_candidate, verbs_db or {})

            action_text = f"[{clean_marker}] {oov_res['label']}"

            clause_triplets.append({
                "subject": selected_subject,
                "modality": resolved_modality,
                "action": action_text,
                "verb_lemma": None,
                "oov_candidate": oov_res["candidate"],
                "oov_type": oov_res["kind"],  # 'oov_form', 'oov_lemma', 'noun_construction', 'none'
                "modality_source": modality_source,
                "marker": clean_marker,
                "cards": [],
                "depends_on": [],
                "clause_text": clause,
                "incomplete": True
            })

    return clause_triplets


# Алиас для обратной совместимости
build_triplets_for_clause = build_clause_triplets