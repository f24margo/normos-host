import os
import json
from django.shortcuts import render, redirect
from django.http import JsonResponse, FileResponse, Http404, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from hostui.services import ask_gemini
from hostui.services.normos import analyze_document


def workspace_page(request):
    """Головна сторінка робочого простору (Fast-Check)."""
    context = {}
    if request.method == "POST":
        input_text = request.POST.get("text", "")
        context["result"] = analyze_document(
            input_text, 
            user=request.user if request.user.is_authenticated else None
        )
        context["input_text"] = input_text

    return render(request, "workspace.html", context)


def chat_page(request):
    """Сторінка чату з ШІ-Консультантом та обробник API запитів."""
    if request.method == "POST":
        try:
            user_message = ""
            
            if request.content_type == "application/json":
                data = json.loads(request.body.decode("utf-8"))
                user_message = data.get("message", "")
            else:
                user_message = request.POST.get("message", "")

            if not user_message:
                return JsonResponse({"error": "Порожнє повідомлення"}, status=400)

            if not os.environ.get("GEMINI_API_KEY"):
                return JsonResponse(
                    {"error": "GEMINI_API_KEY не налаштовано на сервері"}, 
                    status=500
                )

            reply = ask_gemini(user_message)

            return JsonResponse({
                "status": "success",
                "reply": reply,
                "response": reply
            })

        except Exception as e:
            return JsonResponse({"error": f"Помилка сервера: {str(e)}"}, status=500)

    return render(request, "chat.html")


def documents_page(request):
    """Сторінка реєстру, еталонних зразків та нормативних актів."""
    documents_list = [
        {
            "id": "context_markers_uk",
            "title": "Маркери юридичного контексту (JSON)",
            "category": "Словники та Класифікатори",
            "description": "База контекстних слів і маркерів для лінгвістичного аналізу укр. законодавства.",
            "file_type": "JSON",
            "filename": "context_markers_uk.json"
        },
        {
            "id": "norm_verbs_uk",
            "title": "Словник нормативних дієслів (JSON)",
            "category": "Нормопроектувальна техніка",
            "description": "Класифікатор модальностей, обов'язків та заборон у проєктах рішень ОМС.",
            "file_type": "JSON",
            "filename": "norm_verbs_uk.json"
        },
        {
            "id": "reglament_sample",
            "title": "Еталонний Регламент ради ОМС (Шаблон)",
            "category": "Еталонні зразки",
            "description": "Примірний регламент місцевої ради з інтегрованими вимогами антикорупційної експертизи.",
            "file_type": "DOCX",
            "filename": "reglament_sample.docx"
        },
        {
            "id": "decision_project_sample",
            "title": "Проєкт рішення про місцевий бюджет (Еталон)",
            "category": "Еталонні зразки",
            "description": "Типовий проєкт рішення з дотриманням вимог Бюджетного кодексу України.",
            "file_type": "DOCX",
            "filename": "decision_project_sample.docx"
        }
    ]
    return render(request, "documents.html", {"documents": documents_list})


def download_document(request, doc_id):
    """Скачування обраного документа або базового файлу."""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    
    # 1. Перевірка системних json файлів у папці /data/
    file_map = {
        "context_markers_uk": os.path.join(data_dir, "context_markers_uk.json"),
        "norm_verbs_uk": os.path.join(data_dir, "norm_verbs_uk.json"),
        "oov_log": os.path.join(data_dir, "oov_log.jsonl"),
    }

    if doc_id in file_map and os.path.exists(file_map[doc_id]):
        return FileResponse(open(file_map[doc_id], "rb"), as_attachment=True, filename=os.path.basename(file_map[doc_id]))

    # 2. Якщо це демо/еталонний файл, генеруємо текстовий вміст
    demo_content = f"Це еталонний файл нормативно-правового акту для модуля: {doc_id}\n\nСгенеровано системою NormOS Host."
    response = HttpResponse(demo_content, content_type="text/plain; charset=utf-8")
    response['Content-Disposition'] = f'attachment; filename="{doc_id}.txt"'
    return response