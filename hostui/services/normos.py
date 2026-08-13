import os
import re
from typing import List, Dict, Any

def extract_text_from_file(uploaded_file) -> str:
    """Извлечение текста из файлов .txt, .docx, .pdf"""
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    
    try:
        if ext == ".txt":
            return uploaded_file.read().decode("utf-8", errors="ignore")
        
        if ext == ".docx":
            import docx
            doc = docx.Document(uploaded_file)
            return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            
        if ext == ".pdf":
            import pypdf
            reader = pypdf.PdfReader(uploaded_file)
            return "\n".join([page.extract_text() or "" for page in reader.pages])
    except Exception as e:
        print(f"Помилка читання файла {uploaded_file.name}: {e}")
        
    return ""

def filter_header_metadata(text: str) -> str:
    """Очищает текст от служебных шапок грифов утверждения."""
    lines = text.splitlines()
    filtered_lines = []
    
    for line in lines:
        stripped = line.strip()
        if re.match(r'^(ЗАТВЕРДЖЕНО|ДОДАТОК|РІШЕННЯ|ПРОЄКТ|ЗАТВЕРДЖЕНИЙ)\b', stripped, re.IGNORECASE):
            continue
        if stripped:
            filtered_lines.append(stripped)
            
    return "\n".join(filtered_lines) if filtered_lines else text


def analyze_document(text: str = "", *, file=None, user=None, tenant=None) -> dict:
    """
    Базовый логический движок анализа документов МСУ.
    """
    extracted_text = ""
    if file:
        extracted_text = extract_text_from_file(file)
        
    raw_text = (text or extracted_text).strip()
    
    if not raw_text:
        return {
            "ok": False,
            "error": "Не вдалося прочитати текст з файла або поле порожнє.",
            "extracted_text": "",
            "verdict": None, "cards": [], "warnings": [], "hints": []
        }

    body_text = filter_header_metadata(raw_text)
    
    cards: List[Dict[str, Any]] = []
    hints: List[Dict[str, Any]] = []
    warnings: List[str] = []

    # 1. Проверка ссылки на базовый Закон о МСУ (Закон № 280/97-ВР)
    has_msu_law = bool(re.search(r'місцеве\s+самоврядування|280/97', body_text, re.IGNORECASE))
    if has_msu_law:
        cards.append({
            "id": "ЗУ-280",
            "title": "Правова підстава: ЗУ «Про місцеве самоврядування в Україні»",
            "source": {"text_quote": "Встановлено правовий зв'язок з компетенцією органів місцевого самоврядування."}
        })
    else:
        hints.append({
            "text": "У тексті відсутнє пряме посилання на Закон України «Про місцеве самоврядування в Україні». Рекомендовано вказати правову підставу.",
            "level": "warning"
        })

    # 2. Анализ модальности (Обязанности / Запреты / Права)
    has_obligations = bool(re.search(r'\b(зобов\'язаний|зобов\'язані|повинен|повинні|забезпечити|дотримуватись)\b', body_text, re.IGNORECASE))
    has_rights = bool(re.search(r'\b(має\s+право|мають\s+право|вправі|може)\b', body_text, re.IGNORECASE))
    has_prohibitions = bool(re.search(r'\b(забороняється|не\040допускається|обмежено)\b', body_text, re.IGNORECASE))

    if has_obligations:
        cards.append({
            "id": "OBLG-01",
            "title": "Імперативна норма (Зобов'язання)",
            "source": {"text_quote": "Проєкт містить чіткі приписи та зобов'язання щодо виконання дій."}
        })

    # 3. Проверка наличия ответственных и сроков контроля
    has_control_clause = bool(re.search(r'контроль\s+за\s+виконанням|покласти\s+на', body_text, re.IGNORECASE))
    if has_control_clause:
        cards.append({
            "id": "CTRL-01",
            "title": "Норма про контроль виконання",
            "source": {"text_quote": "Визначено відповідальних осіб або комісію за здійснення контролю."}
        })
    else:
        hints.append({
            "text": "Не знайдено пункт про контроль за виконанням рішення (наприклад: 'Контроль за виконанням покласти на...').",
            "level": "info"
        })

    # 4. Общая подсказка о прочитанных символах
    hints.append({
        "text": f"Проаналізовано {len(raw_text)} символів. Шапку грифа затвердження відфільтровано.",
        "level": "info"
    })

    # Определяем вердикт на основе найденных конструкций
    modality = "OBLG" if has_obligations else ("PERM" if has_rights else "NORM")
    deciding_verb = "зобов'язаний виконати" if has_obligations else "має право / нормує"

    return {
        "ok": True,
        "extracted_text": raw_text,
        "verdict": {
            "headline": "Аналіз відповідності вимогам МСУ",
            "deciding_verb": deciding_verb,
            "agent": "Орган місцевого самоврядування / Виконавець",
            "modality": modality
        },
        "cards": cards,
        "warnings": warnings,
        "hints": hints,
        "meta": {"char_count": len(raw_text)},
        "disclaimer": "Результат є попереднім автоматичним аналізом."
    }