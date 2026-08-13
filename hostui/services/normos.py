import json
import re
from pathlib import Path
from django.conf import settings

INDEX_CACHE = {}

def normalize_text(text: str) -> str:
    """Нормализует апострофы и регистр для точного поиска."""
    return re.sub(r"[’`ʼ]", "'", text).lower()

def load_indexes():
    """Загружает индексы пакета msu_ua в память при первом обращении."""
    if INDEX_CACHE:
        return INDEX_CACHE

    pkg_dir = Path(settings.BASE_DIR) / "packages" / "msu_ua"
    index_dir = pkg_dir / "index"
    cards_dir = pkg_dir / "cards"
    
    by_verb_file = index_dir / "by_verb.json"
    by_agent_file = index_dir / "by_agent.json"

    by_verb = json.load(open(by_verb_file, "r", encoding="utf-8")) if by_verb_file.exists() else {}
    by_agent = json.load(open(by_agent_file, "r", encoding="utf-8")) if by_agent_file.exists() else {}

    # Загрузка описаний карточек (включая depends_on)
    cards_db = {}
    if cards_dir.exists():
        for card_file in cards_dir.glob("*.json"):
            try:
                cdata = json.load(open(card_file, "r", encoding="utf-8"))
                cid = cdata.get("id") or card_file.stem
                cards_db[cid] = cdata
            except Exception:
                pass

    INDEX_CACHE["by_verb"] = by_verb
    INDEX_CACHE["by_agent"] = by_agent
    INDEX_CACHE["cards_db"] = cards_db
    return INDEX_CACHE

def get_oov_queue_path() -> Path:
    data_dir = Path(settings.BASE_DIR) / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir / "oov_queue.json"

def record_oov_proposal(lemma: str, oov_type: str, source: str = "host_ui") -> dict:
    """Записывает предложение OOV в единый персистентный лог."""
    path = get_oov_queue_path()
    queue = {}
    if path.exists():
        try:
            queue = json.load(open(path, "r", encoding="utf-8"))
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

# --- NKS-012 MODALITY PATTERNS ---
MODALITY_PATTERNS = [
    # 1. Отрицания и Запреты (PROH)
    {"pattern": r"\bне має права\b", "cat": "PROH", "negated": True, "raw": "не має права"},
    {"pattern": r"\bне може\b", "cat": "PROH", "negated": True, "raw": "не може"},
    {"pattern": r"\bне допускається\b", "cat": "PROH", "negated": True, "raw": "не допускається"},
    {"pattern": r"\bне вправі\b", "cat": "PROH", "negated": True, "raw": "не вправі"},
    {"pattern": r"\bзабороняється\b", "cat": "PROH", "negated": False, "raw": "забороняється"},

    # 2. Снятие обязанности / Снятие запрета (PERM)
    {"pattern": r"\bне зобов'язаний\b", "cat": "PERM", "negated": True, "raw": "не зобов'язаний"},
    {"pattern": r"\bне повинен\b", "cat": "PERM", "negated": True, "raw": "не повинен"},
    {"pattern": r"\bне забороняється\b", "cat": "PERM", "negated": True, "raw": "не забороняється"},
    {"pattern": r"\bмає право не\b", "cat": "PERM", "negated": True, "raw": "має право не"},

    # 3. Прямые обязанности (OBL)
    {"pattern": r"\bзобов'язаний\b", "cat": "OBL", "negated": False, "raw": "зобов'язаний"},
    {"pattern": r"\bповинен\b", "cat": "OBL", "negated": False, "raw": "повинен"},
    {"pattern": r"\bзабезпечує\b", "cat": "OBL", "negated": False, "raw": "забезпечує"},
    {"pattern": r"\bздійснює\b", "cat": "OBL", "negated": False, "raw": "здійснює"},

    # 4. Прямые права (PERM)
    {"pattern": r"\bмає право\b", "cat": "PERM", "negated": False, "raw": "має право"},
    {"pattern": r"\bвправі\b", "cat": "PERM", "negated": False, "raw": "вправі"},
]

def find_agent_forms_in_text(text: str, by_agent: dict) -> list:
    """Возвращает список всех найденных форм ролей с метаданными."""
    found = []
    norm_t = normalize_text(text)
    for agent_key, agent_info in by_agent.items():
        forms = agent_info.get("forms", [agent_key])
        lemma = agent_info.get("lemma", agent_key)
        
        for form_idx, form in enumerate(forms):
            pattern = re.compile(r'\b' + re.escape(normalize_text(form)) + r'\b', re.IGNORECASE)
            for match in pattern.finditer(norm_t):
                found.append({
                    "start": match.start(),
                    "end": match.end(),
                    "matched_text": text[match.start():match.end()],
                    "lemma": lemma,
                    "is_nominative": (form_idx == 0) # Полномочный субъект (Именительный падеж)
                })
    return sorted(found, key=lambda x: x["start"])

def split_into_clauses(text: str, by_agent: dict) -> list:
    """
    Разбивает текст на клаузы.
    Запятая РАЗРЫВАЕТ клаузу только если после нее идет новый субъект из by_agent.
    """
    clause_splits = re.split(r'(?<=[\.\;\n])|\b(але|щоб|який|якщо|тому що)\b', text, flags=re.IGNORECASE)
    clauses = []
    
    for raw in clause_splits:
        if not raw or raw.strip() in ["але", "щоб", "який", "якщо", "тому що"]:
            continue
        
        sub_parts = raw.split(",")
        current_acc = ""
        for i, part in enumerate(sub_parts):
            if i == 0:
                current_acc = part
                continue
            
            has_agent_after = len(find_agent_forms_in_text(part, by_agent)) > 0
            if has_agent_after:
                clauses.append(current_acc)
                current_acc = part
            else:
                current_acc += "," + part
        if current_acc:
            clauses.append(current_acc)

    return [c.strip() for c in clauses if c.strip()]

def is_normative_context(word_span: tuple, text: str, by_agent: dict) -> bool:
    """Контекстный фильтр нормативности с динамическим извлечением маркеров."""
    start, end = word_span
    window_start = max(0, start - 80)
    window_end = min(len(text), end + 80)
    snippet = text[window_start:window_end].lower()

    for mp in MODALITY_PATTERNS:
        if mp["raw"] in snippet:
            return True

    if len(find_agent_forms_in_text(snippet, by_agent)) > 0:
        return True

    return False

def analyze_document(text: str, layers: list = None) -> dict:
    if layers is None:
        layers = ["verbs", "modality", "roles", "msu"]

    indexes = load_indexes()
    by_verb = indexes.get("by_verb", {})
    by_agent = indexes.get("by_agent", {})
    cards_db = indexes.get("cards_db", {})

    spans = []
    triplets = []
    norm_text = normalize_text(text)
    
    exact_hits = 0
    root_hits = 0

    # 1. Поиск ролей (Roles) по документу
    all_role_matches = find_agent_forms_in_text(text, by_agent)
    if "roles" in layers:
        for rmatch in all_role_matches:
            spans.append({
                "start": rmatch["start"],
                "end": rmatch["end"],
                "layer": "roles",
                "class": "layer-role",
                "lemma": rmatch["lemma"],
                "is_nominative": rmatch["is_nominative"],
                "label": f"Роль: {rmatch['lemma']} ({'Им.падеж' if rmatch['is_nominative'] else 'Косв.падеж'})"
            })

    # 2. Находим все глаголы из реестра по документу
    matched_verbs_list = []
    matched_verb_spans = set()

    for verb, card_ids in by_verb.items():
        norm_verb = normalize_text(verb)
        if not norm_verb or len(norm_verb) < 3:
            continue

        pattern = re.compile(r'\b' + re.escape(norm_verb) + r'\b', re.IGNORECASE)
        for match in pattern.finditer(norm_text):
            start, end = match.span()
            matched_verb_spans.add((start, end))
            exact_hits += 1

            matched_verbs_list.append({
                "start": start,
                "end": end,
                "verb": verb,
                "text": text[start:end],
                "card_ids": card_ids
            })

            if "verbs" in layers:
                spans.append({
                    "start": start,
                    "end": end,
                    "layer": "verbs",
                    "class": "layer-verb",
                    "match_type": "exact",
                    "label": f"Дія: {text[start:end]}"
                })

            if "msu" in layers:
                for cid in card_ids:
                    spans.append({
                        "start": start,
                        "end": end,
                        "layer": "msu",
                        "class": "layer-msu",
                        "card_id": cid,
                        "label": f"Норма {cid}"
                    })

    # 3. Анализ Модальности и Сборка Триплетов по клаузам
    clauses = split_into_clauses(text, by_agent)
    clause_offset = 0

    for clause in clauses:
        clause_start = text.find(clause, clause_offset)
        if clause_start == -1:
            clause_start = clause_offset
        clause_end = clause_start + len(clause)
        clause_offset = clause_end

        norm_clause = normalize_text(clause)
        found_markers = []
        consumed_spans = []

        # Поиск модальных маркеров
        for mp in MODALITY_PATTERNS:
            for match in re.finditer(mp["pattern"], norm_clause, re.IGNORECASE):
                span = (clause_start + match.start(), clause_start + match.end())
                if any(span[0] >= cs and span[1] <= ce for cs, ce in consumed_spans):
                    continue

                found_markers.append({
                    "cat": mp["cat"],
                    "negated": mp["negated"],
                    "match": match.group(0),
                    "start": span[0],
                    "end": span[1]
                })
                consumed_spans.append(span)

        # Проверка "може" (ROLE + може + INF)
        if "може" in norm_clause and not any(m["match"] == "не може" for m in found_markers):
            clause_roles = find_agent_forms_in_text(clause, by_agent)
            has_role = len(clause_roles) > 0
            has_inf = bool(re.search(r'\b\w+(ти|тись|тися)\b', norm_clause, re.IGNORECASE))
            if has_role and has_inf:
                m_match = re.search(r'\bможе\b', norm_clause, re.IGNORECASE)
                if m_match:
                    m_span = (clause_start + m_match.start(), clause_start + m_match.end())
                    if not any(m_span[0] >= cs and m_span[1] <= ce for cs, ce in consumed_spans):
                        found_markers.append({
                            "cat": "PERM",
                            "negated": False,
                            "match": "може",
                            "start": m_span[0],
                            "end": m_span[1]
                        })

        # Определение категории модальности
        final_cat = "OBL"
        source_enum = "registry_default"
        applied_marker = "registry_default"

        if found_markers:
            categories = set(m["cat"] for m in found_markers)
            if len(categories) > 1:
                source_enum = "conflict_default"
                final_cat = "PROH" if "PROH" in categories else ("OBL" if "OBL" in categories else "PERM")
            else:
                marker = found_markers[0]
                final_cat = marker["cat"]
                source_enum = "negation_scope_applied" if marker["negated"] else "explicit_clause_marker"
            applied_marker = found_markers[0]["match"]

            if "modality" in layers:
                for m in found_markers:
                    spans.append({
                        "start": m["start"],
                        "end": m["end"],
                        "layer": "modality",
                        "class": f"modality-{final_cat.lower()}",
                        "category": final_cat,
                        "modality_source": source_enum,
                        "marker": m["match"],
                        "label": f"Модальність: {final_cat} ({m['match']})"
                    })

        # Выбор субъекта с приоритетом именительного падежа (Nominative Priority)
        clause_roles = [r for r in all_role_matches if clause_start <= r["start"] and r["end"] <= clause_end]
        selected_subject = None
        
        # 1. Сначала ищем роль в Именительном падеже
        nominative_roles = [r for r in clause_roles if r["is_nominative"]]
        if nominative_roles:
            selected_subject = nominative_roles[0]["lemma"]
        elif clause_roles:
            # Если именительного нет, берем первую
            selected_subject = clause_roles[0]["lemma"]

        # Находим все действия (Verbs) внутри клаузы для декомпозиции 1-к-N
        clause_verbs = [v for v in matched_verbs_list if clause_start <= v["start"] and v["end"] <= clause_end]

        if clause_verbs:
            for v_item in clause_verbs:
                # Чтениеdepends_on из карточек МСУ
                depends_on_list = []
                for cid in v_item["card_ids"]:
                    card_data = cards_db.get(cid, {})
                    if "depends_on" in card_data:
                        depends_on_list.extend(card_data["depends_on"])

                triplets.append({
                    "subject": selected_subject, # None = subject: null (Загальна норма)
                    "modality": final_cat,
                    "action": v_item["text"],
                    "verb_lemma": v_item["verb"],
                    "modality_source": source_enum,
                    "marker": applied_marker,
                    "cards": v_item["card_ids"],
                    "depends_on": list(set(depends_on_list)),
                    "clause_text": clause
                })
        elif found_markers:
            # Безглагольная клауза с явно выраженным модальным маркером
            triplets.append({
                "subject": selected_subject,
                "modality": final_cat,
                "action": "дію не вказано",
                "verb_lemma": None,
                "modality_source": source_enum,
                "marker": applied_marker,
                "cards": [],
                "depends_on": [],
                "clause_text": clause
            })

    # 4. Извлечение OOV с мотивированным морфологическим порогом (корень >= 6)
    verb_pattern = re.compile(r'\b\w+(ти|ться|ть|ють|ають|ують|еться)\b', re.IGNORECASE)
    oov_forms = {}
    oov_lemmas = {}
    total_normative_candidates = exact_hits

    for match in verb_pattern.finditer(norm_text):
        start, end = match.span()
        if (start, end) in matched_verb_spans:
            continue

        word = text[start:end]
        if len(word) < 4:
            continue

        if not is_normative_context((start, end), norm_text, by_agent):
            continue

        total_normative_candidates += 1
        norm_word = normalize_text(word)

        has_root_match = False
        if len(norm_word) >= 6:
            for known_verb in by_verb.keys():
                norm_known = normalize_text(known_verb)
                if len(norm_known) >= 6 and norm_word[:6] == norm_known[:6]:
                    has_root_match = True
                    break

        if has_root_match:
            oov_forms[norm_word] = oov_forms.get(norm_word, 0) + 1
            root_hits += 1
        else:
            oov_lemmas[norm_word] = oov_lemmas.get(norm_word, 0) + 1

    strict_coverage = (exact_hits / total_normative_candidates * 100) if total_normative_candidates > 0 else 0.0
    root_bonus = (root_hits / total_normative_candidates * 100) if total_normative_candidates > 0 else 0.0

    spans.sort(key=lambda x: (x["start"], -(x["end"] - x["start"])))

    return {
        "text": text,
        "active_layers": layers,
        "spans": spans,
        "triplets": triplets,
        "metrics": {
            "strict_coverage": round(strict_coverage, 1),
            "root_bonus": round(root_bonus, 1),
            "exact_hits": exact_hits,
            "root_hits": root_hits,
            "normative_candidates": total_normative_candidates
        },
        "oov": {
            "forms": [{"word": k, "count": v} for k, v in sorted(oov_forms.items(), key=lambda x: -x[1])],
            "lemmas": [{"word": k, "count": v} for k, v in sorted(oov_lemmas.items(), key=lambda x: -x[1])]
        },
        "matched_cards_count": len(set(s.get("card_id") for s in spans if "card_id" in s)),
        "status": "success"
    }