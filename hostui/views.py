import json
import os
from django.shortcuts import render, redirect
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from hostui.services import ask_gemini


def workspace_page(request):
    """Головна сторінка робочого простору (Fast-Check)."""
    return render(request, "workspace.html")


def chat_page(request):
    """Сторінка чату з ШІ-Консультантом та обробник API запитів."""
    if request.method == "POST":
        try:
            user_message = ""
            
            # Обробка запитів у форматі JSON або Form-data
            if request.content_type == "application/json":
                data = json.loads(request.body.decode("utf-8"))
                user_message = data.get("message", "")
            else:
                user_message = request.POST.get("message", "")

            if not user_message:
                return JsonResponse({"error": "Порожнє повідомлення"}, status=400)

            # Перевірка наявності API ключа
            if not os.environ.get("GEMINI_API_KEY"):
                return JsonResponse(
                    {"error": "GEMINI_API_KEY не налаштовано на сервері"}, 
                    status=500
                )

            # Отримання відповіді від ШІ сервісу
            reply = ask_gemini(user_message)

            # Повертаємо ключі reply та response для повної сумісності з JS
            return JsonResponse({
                "status": "success",
                "reply": reply,
                "response": reply
            })

        except Exception as e:
            return JsonResponse({"error": f"Помилка сервера: {str(e)}"}, status=500)

    # При GET запиті віддаємо HTML сторінку чату
    return render(request, "chat.html")


def documents_page(request):
    """Сторінка реєстру та архіву документів."""
    return render(request, "documents.html")


def download_document(request, doc_id):
    """Скачування обробленого документа або аналітичного звіту."""
    # Логіка для скачування файлів (якщо потрібно розширити)
    file_path = os.path.join("data", f"{doc_id}.json")
    if os.path.exists(file_path):
        return FileResponse(open(file_path, "rb"), as_attachment=True)
    raise Http404("Документ не знайдено")