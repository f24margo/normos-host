import re
from hostui.services.registry import RegistryService
from hostui.services.parser import normalize_text, split_into_clauses
from hostui.services.roles import find_agent_forms_in_text
from hostui.services.triplets import build_clause_triplets
from hostui.services.recommender import generate_recommendations

MODALITY_PATTERNS = [
    # 1. Запреты (PROH)
    {"pattern": r"\bне має права\b", "cat": "PROH", "negated": True, "raw": "не має права"},
    {"pattern": r"\bне може\b", "cat": "PROH", "negated": True, "raw": "не може"},
    {"pattern": r"\bне допускається\b", "cat": "PROH", "negated": True, "raw": "не допускається"},
    {"pattern": r"\bне вправі\b", "cat": "PROH", "negated": True, "raw": "не вправі"},
    {"pattern": r"\bзабороняється\b", "cat": "PROH", "negated": False, "raw": "забороняється"},

    # 2. Снятие обязанности / Дозволение (PERM)
    {"pattern": r"\bне зобов'язаний\b", "cat": "PERM", "negated": True, "raw": "не зобов'язаний"},
    {"pattern": r"\bне повинен\b", "cat": "PERM", "negated": True, "raw": "не повинен"},
    {"pattern": r"\bне забороняється\b", "cat": "PERM", "negated": True, "raw": "не забороняється"},
    {"pattern": r"\bмає право не\b", "cat": "PERM", "negated": True, "raw": "має право не"},

    # 3. Обязанности (OBL)
    {"pattern": r"\bзобов'язаний\b", "cat": "OBL", "negated": False, "raw": "зобов'язаний"},
    {"pattern": r"\bповинен\b", "cat": "OBL", "negated": False, "raw": "повинен"},
    {"pattern": r"\bзабезпечує\b", "cat": "OBL", "negated": False, "raw": "забезпечує"},
    {"pattern": r"\bздійснює\b", "cat": "OBL", "negated": False, "raw": "здійснює"},

    # 4. Права (PERM)
    {"pattern": r"\bмає право\b", "cat": "PERM", "negated": False, "raw": "має право"},
    {"pattern": r"\bвправі\b", "cat": "PERM", "negated": False, "raw": "вправі"},
]

def is_normative_context(word_span: tuple, text: str, agents_db: dict) -> bool:
    """Контекстный фильтр нормативности с извлечением маркеров."""
    start, end = word_span
    snippet = text[max(0, start - 80):min(len(text), end + 80)].lower()

    for mp in MODALITY_PATTERNS:
        if mp["raw"] in snippet:
            return True

    if len(find_agent_forms_in_text(snippet, agents_db)) > 0:
        return True

    return False

def analyze_document_pipeline(text: str, layers: list = None, registry: RegistryService = None) -> dict:
    if layers is None:
        layers = ["verbs", "modality", "roles", "msu"]

    if registry is None:
        registry = RegistryService()

    spans = []
    triplets = []
    norm_text = normalize_text(text)
    
    exact_hits = 0
    root_hits = 0

    # 1. Поиск Ролей
    all_role_matches = find_agent_forms_in_text(text, registry.agents_db)
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

    # 2. Поиск Глаголов
    matched_verbs_list = []
    matched_verb_spans = set()

    for verb, card_ids in registry.verbs_db.items():
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

    # 3. Разбор клауз, Модальности и Сборка триплетов
    clauses = split_into_clauses(text, registry)
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

        if "може" in norm_clause and not any(m["match"] == "не може" for m in found_markers):
            clause_roles = find_agent_forms_in_text(clause, registry.agents_db)
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

        clause_triplets = build_clause_triplets(
            clause=clause,
            clause_start=clause_start,
            clause_end=clause_end,
            all_role_matches=all_role_matches,
            matched_verbs_list=matched_verbs_list,
            found_markers=found_markers,
            final_modality_cat=final_cat,
            modality_source=source_enum,
            applied_marker=applied_marker,
            cards_db=registry.cards_db
        )
        triplets.extend(clause_triplets)

    # 4. Детекция OOV
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

        if not is_normative_context((start, end), norm_text, registry.agents_db):
            continue

        total_normative_candidates += 1
        norm_word = normalize_text(word)

        has_root_match = False
        if len(norm_word) >= 6:
            for known_verb in registry.verbs_db.keys():
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

    # Генерируем рекомендации
    recommendations = generate_recommendations(triplets)

    return {
        "text": text,
        "active_layers": layers,
        "spans": spans,
        "triplets": triplets,
        "recommendations": recommendations,
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