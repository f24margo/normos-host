import json
import os
from google import genai
from django.conf import settings

# Загружаем базу знаний ТРИЗ при старте сервера
TRIZ_FILE_PATH = os.path.join(settings.BASE_DIR, 'hostui', 'triz_data.json')
TRIZ_CONTEXT_STR = ""

if os.path.exists(TRIZ_FILE_PATH):
    with open(TRIZ_FILE_PATH, 'r', encoding='utf-8') as f:
        TRIZ_CONTEXT_STR = f.read()

ROLE_PROMPTS = {
    "triz": f"""Ти — експерт з прийняття рішень за методологією ТРИЗ у системі NormOS.

Твоя задача: НЕ вигадувати рішення, а працювати як інженер системи.

ОСЬ ТВОЯ БАЗА ДАНИХ (СТРУКТУРА ТРИЗ ДЛЯ ГРОМАД):
{TRIZ_CONTEXT_STR}

АЛГОРИТМ:
1. КРОК 1 — Уточнення задачі (якщо бракує даних — задай 1–2 питання).
2. КРОК 2 — Формування протиріччя ("Ми хочемо покращити X, але це погіршує Y").
3. КРОК 3 — Вибір принципів (знайди їх у матриці).
4. КРОК 4 — Генерація рішень (використай шаблони з principles та приклади для громад).
5. КРОК 5 — Пояснення (1–2 речення).

ФОРМАТ ВІДПОВІДІ:
📊 Протиріччя: ...
🧠 Принципи: ...
💡 Рішення:
1. ...
2. ...

ВАЖЛИВО: Використовуй ТІЛЬКИ принципи та шаблони з наданої бази даних!""",

    "product_help": """Ты — ассистент по поддержке NormOS. Помогай пользователю освоить интерфейс и функции системы. Отвечай кратко и по делу.""",

    "legal_guardrail": """Ты — модуль проверки регламентов NormOS. 
КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО давать юридические консультации и официальные правовые заключения. 
Твоя задача — подсвечивать потенциальные процедурные риски в текстах решений и перенаправлять пользователя к юридическому отделу."""
}


def ask_gemini(user_message: str, role: str = "triz", history: list = None) -> str:
    """
    Отправляет запрос к Gemini API с учетом выбранной роли и истории.
    """
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    system_instruction = ROLE_PROMPTS.get(role, ROLE_PROMPTS["triz"])
    
    contents = []
    if history:
        for msg in history:
            r = msg.get("role")
            t = msg.get("parts", [""])[0] if isinstance(msg.get("parts"), list) else msg.get("message", "")
            if t:
                contents.append(f"{'Користувач' if r == 'user' else 'Асистент'}: {t}")
            
    contents.append(f"Користувач: {user_message}")
    
    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents="\n".join(contents),
        config={"system_instruction": system_instruction}
    )
    
    return response.text