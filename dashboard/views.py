from django.shortcuts import render

from accounts.decorators import gate_staff_required

from . import preview


@gate_staff_required
def home(request):
    return render(
        request,
        "dashboard/index.html",
        {
            "section": "overview",
            "stats": preview.stats(),
            "visitors": preview.visitors()[:4],
            "events": preview.events(),
            "mix": preview.mix(),
            "trend": preview.trend(),
        },
    )


@gate_staff_required
def visitor_list(request):
    return render(
        request,
        "dashboard/visitors.html",
        {
            "section": "visitors",
            "visitors": preview.visitors(),
        },
    )


@gate_staff_required
def visit_detail(request, reference):
    visit = preview.visitor(reference)
    return render(
        request,
        "dashboard/visit_detail.html",
        {"section": "visitors", "visit": visit},
        status=200 if visit else 404,
    )


@gate_staff_required
def gate_log(request):
    return render(
        request,
        "dashboard/gate_log.html",
        {
            "section": "log",
            "events": preview.events(),
        },
    )
