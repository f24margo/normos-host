import re
from hostui.services.registry import RegistryService

def normalize_text(text: str) -> str:
    """Нормализует апострофы и регистр для точного поиска."""
    return re.sub(r"[’`ʼ]", "'", text).lower()

def split_into_clauses(text: str, registry: RegistryService) -> list:
    """
    Разбивает текст на клаузы.
    Запятая РАЗРЫВАЕТ клаузу только если после нее идет новый субъект из by_agent.
    """
    from hostui.services.roles import find_agent_forms_in_text

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
            
            has_agent_after = len(find_agent_forms_in_text(part, registry.agents_db)) > 0
            if has_agent_after:
                clauses.append(current_acc)
                current_acc = part
            else:
                current_acc += "," + part
        if current_acc:
            clauses.append(current_acc)

    return [c.strip() for c in clauses if c.strip()]