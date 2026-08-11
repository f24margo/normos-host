import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render

from .services import ask_gemini

try:
    from hostui.analysis import analyze_text
except ImportError:
    analyze_text = None

# База образцов нормативно-правовых актов ОМС
SAMPLE_DOCS = {
    "reglement_excom": {
        "title": "Проєкт рішення: Регламент виконавчого комітету",
        "category": "Регламенти та органи",
        "description": "Типовий проєкт рішення міської ради про затвердження порядку діяльності виконкому, процедур скликання та прийняття рішень.",
        "filename": "Proekt_Rishennya_Reglament_Vykonkomu.txt",
        "content": """МІСЬКА РАДА
VIII СЕСІЯ
ПРОЄКТ РІШЕННЯ

Про затвердження Регламенту виконавчого комітету міської ради

Керуючись ст. 26, ст. 51, ст. 59 Закону України «Про місцеве самоврядування в Україні», міська рада ВИРІШИЛА:

1. Затвердити Регламент виконавчого комітету міської ради (додається).
2. Визнати таким, що втратило чинність, рішення міської ради від 15.12.2020 № 45-VIII «Про Регламент виконавчого комітету».
3. Контроль за виконанням даного рішення покласти на секретаря міської ради та постійну комісію з питань регламенту, депутатської етики та законності.

Міський голова ______________________ (Підпис)
"""
    },
    "public_hearings": {
        "title": "Положення: Публічні слухання та е-петиції",
        "category": "Громадська участь",
        "description": "Положення про порядок організації консультацій з громадськістю, внесення електронних петицій та проведення загальних зборів.",
        "filename": "Polozhennya_Public_Consultations.txt",
        "content": """ЗАТВЕРДЖЕНО
Рішенням міської ради
від _________ 2026 року № _____

ПОЛОЖЕННЯ
про консультації з громадськістю та електронні петиції в громаді

1. Загальні положення
1.1. Це Положення визначає порядок ініціювання, підготовки та проведення консультацій з громадськістю щодо проєктів актів органів місцевого самоврядування.
1.2. Метою проведення консультацій є залучення жителів громади до прийняття управлінських рішень та врахування їх інтересів.

2. Порядок подання та розгляду електронних петицій
2.1. Громадяни можуть звертатися до міської ради з електронними петиціями через офіційний веб-портал.
2.2. Петиція розглядається за умови збору на її підтримку не менш як 250 підписів протягом 30 днів з дня оприлюднення.
2.3. Проєкт рішення за результатами розгляду петиції готується профільним виконавчим органом протягом 14 робочих днів.
"""
    },
    "cnap_services": {
        "title": "Порядок: Інформаційні картки адмінпослуг (ЦНАП)",
        "category": "Регламенти послуг",
        "description": "Стандартизований порядок затвердження та оновлення інформаційних і технологічних карток адміністративних послуг.",
        "filename": "Poryadok_Karty_CNAP.txt",
        "content": """ЗАТВЕРДЖЕНО
Розпорядження міського голови
від _________ 2026 року № _____

ПОРЯДОК
затвердження та актуалізації інформаційних карток адміністративних послуг

1. Загальні вимоги
1.1. Інформаційна картка адміністративної послуги містить повну та вичерпну інформацію щодо суб'єкта надання послуги, строків, переліку документів та підстав для відмови.
1.2. Розробка карток здійснюється суб'єктом надання послуги протягом 10 днів після набрання чинності нормативним актом, що регулює надання послуги.

2. Контроль якості та публікація
2.1. Усі картки проходять обов'язкову процедуру перевірки в Центрі надання адміністративних послуг (ЦНАП) на відповідність вимогам Закону України «Про адміністративні послуги».
2.2. Затверджені картки оприлюднюються на офіційному веб-сайті громади протягом 3 робочих днів.
"""
    }
}


@login_required
def workspace(request):
    """Страница рабочего пространства."""
    profile = getattr(request.user, "profile", None)
    context = {
        "profile": profile,
        "result": None,
        "text": "",
    }

    if request.method == "POST":
        text = request.POST.get("text") or ""
        context["text"] = text
        if analyze_text:
            context["result"] = analyze_text(text)

    return render(request, "workspace.html", context)


# Псевдоним для маршрутизатора
workspace_page = workspace


@login_required
def chat_page(request):
    """Страница интерактивного чата."""
    return render(request, "chat.html")


@login_required
def chat_api(request):
    """API-обработчик запросов к Gemini с выбором роли."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_message = data.get("message", "")
            role = data.get("role", "triz")
            history = data.get("history", [])

            if not user_message:
                return JsonResponse({"error": "Порожнє повідомлення"}, status=400)

            reply = ask_gemini(user_message, role=role, history=history)
            return JsonResponse({"reply": reply})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@login_required
def documents_page(request):
    """Страница со списком образцов документов."""
    return render(request, "documents.html", {"documents": SAMPLE_DOCS})


@login_required
def download_document(request, doc_id):
    """Скачивание файла документа на рабочий стол."""
    doc = SAMPLE_DOCS.get(doc_id)
    if not doc:
        return JsonResponse({"error": "Документ не знайдено"}, status=404)

    response = HttpResponse(doc["content"], content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{doc["filename"]}"'
    return response