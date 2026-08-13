import re
from hostui.services.parser import normalize_text

def find_agent_forms_in_text(text: str, agents_db: dict) -> list:
    """
    Возвращает список всех найденных форм ролей в тексте с метаданными.
    Форма с формальным индексом 0 (forms[0]) считается именительным падежом.
    """
    found = []
    norm_t = normalize_text(text)
    
    for agent_key, agent_info in agents_db.items():
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
                    "is_nominative": (form_idx == 0)  # Nominative Priority Flag
                })
                
    return sorted(found, key=lambda x: x["start"])

def select_clause_subject(clause_roles: list) -> str | None:
    """
    Реализует правило Nominative Priority для выбора главного субъекта клаузы:
    1. Ищет роль в Именительном падеже (is_nominative == True).
    2. Если именительного падежа нет — берет первую упомянутую роль.
    3. Если ролей нет — возвращает None (subject: null / загальна норма).
    """
    nominative_roles = [r for r in clause_roles if r.get("is_nominative")]
    if nominative_roles:
        return nominative_roles[0]["lemma"]
    elif clause_roles:
        return clause_roles[0]["lemma"]
    return None