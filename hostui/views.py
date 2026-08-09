from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def workspace(request):
    profile = getattr(request.user, "profile", None)
    context = {
        "profile": profile,
        "result": None,
        "text": "",
    }

    if request.method == "POST":
        text = (request.POST.get("text") or "").strip()
        context["text"] = text
        context["result"] = {
            "char_count": len(text),
            "word_count": len(text.split()) if text else 0,
            "stub": True,
            "message": (
                "Текст прийнято. Повний розбір NormOS буде підключено пізніше "
                "(день 10 roadmap)."
            ),
        }

    return render(request, "workspace.html", context)