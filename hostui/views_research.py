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
from hostui.services import research_registry as reg_svc


@staff_member_required
def research_console(request):
    status = get_system_status()
    return render(request, "research/console.html", {"status": status})


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


# --- 5.4 Registry / OOV ---

@staff_member_required
@require_GET
def research_registry_list_api(request):
    status = request.GET.get("status") or "needs_review"
    if status not in ("needs_review", "reviewed", "default", "all"):
        status = "needs_review"
    return JsonResponse({
        "filter": status,
        "transition_types": list(reg_svc.TRANSITION_TYPES),
        "verbs": reg_svc.list_verbs(status_filter=status),
    })


@staff_member_required
@csrf_exempt
@require_POST
def research_registry_confirm_api(request, verb_id: str):
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        body = {}
    try:
        updated = reg_svc.confirm_transition(
            verb_id=verb_id,
            transition_type=body.get("transition_type"),
        )
        return JsonResponse({"status": "ok", "verb": updated})
    except KeyError as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=404)
    except ValueError as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


@staff_member_required
@require_GET
def research_oov_list_api(request):
    return JsonResponse({"items": reg_svc.list_oov_queue(pending_only=True)})


@staff_member_required
@csrf_exempt
@require_POST
def research_oov_reject_api(request, key: str):
    try:
        return JsonResponse({"status": "ok", **reg_svc.oov_reject(key)})
    except KeyError as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=404)


@staff_member_required
@csrf_exempt
@require_POST
def research_oov_accept_lemma_api(request, key: str):
    try:
        return JsonResponse({"status": "ok", **reg_svc.oov_accept_lemma(key)})
    except KeyError as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=404)


@staff_member_required
@csrf_exempt
@require_POST
def research_oov_accept_form_api(request, key: str):
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        body = {}
    target = (body.get("target_lemma") or "").strip()
    if not target:
        return JsonResponse({"status": "error", "message": "target_lemma required"}, status=400)
    try:
        return JsonResponse({"status": "ok", **reg_svc.oov_accept_form(key, target)})
    except KeyError as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=404)