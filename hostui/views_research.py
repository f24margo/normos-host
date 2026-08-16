"""
NKS-014 Research & Admin Console — views.
Доступ: is_staff / superuser. Без власної логіки аналізу.
"""
from __future__ import annotations

import json

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from hostui.services.research_status import get_system_status
from hostui.services.golden_runner import run_golden_tests
from hostui.services.markup import analyze_document_pipeline


@staff_member_required
def research_console(request):
    status = get_system_status()
    return render(
        request,
        "research/console.html",
        {"status": status},
    )


@staff_member_required
@require_GET
def research_status_api(request):
    return JsonResponse(get_system_status())


@staff_member_required
@csrf_exempt
@require_POST
def research_golden_run_api(request):
    return JsonResponse(run_golden_tests())


@staff_member_required
@csrf_exempt
@require_POST
def research_analyze_api(request):
    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

    text = (data.get("text") or "").strip()
    if not text:
        return JsonResponse({"status": "error", "message": "Empty text"}, status=400)

    layers = data.get("layers") or ["verbs", "modality", "roles", "msu"]
    result = analyze_document_pipeline(text=text, layers=layers)
    result["is_admin_test"] = True
    return JsonResponse(result)