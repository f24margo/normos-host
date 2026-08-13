import json
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from .services.normos import analyze_document, record_oov_proposal

def workspace_page(request):
    return render(request, 'workspace.html')

def chat_page(request):
    return render(request, 'chat.html')

def documents_page(request):
    return render(request, 'documents.html')

def download_document(request, doc_id):
    return HttpResponse(f"Download document {doc_id}", content_type="text/plain")

@csrf_exempt
def analyze_api(request):
    """API-эндпоинт для анализа текста по слоям."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            text = data.get("text", "")
            layers = data.get("layers", ["verbs", "modality", "roles", "msu"])
            
            result = analyze_document(text, layers=layers)
            return JsonResponse(result)
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
            
    return JsonResponse({"status": "error", "message": "Only POST allowed"}, status=405)

@csrf_exempt
def propose_oov_api(request):
    """API-эндпоинт для фиксации OOV-кандидата в queue c disposition: pending."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            lemma = data.get("lemma", "").strip()
            oov_type = data.get("type", "lemma")
            
            if not lemma:
                return JsonResponse({"status": "error", "message": "Empty lemma"}, status=400)
                
            entry = record_oov_proposal(lemma, oov_type=oov_type, source="host_ui")
            return JsonResponse({"status": "success", "entry": entry})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Only POST allowed"}, status=405)