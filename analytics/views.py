import json

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import gate_staff_required
from accounts.roles import ADMINISTRATOR
from dashboard.paging import paginate
from gatepass.models import VisitorVisit

from . import data, insights, ml, training
from .models import ModelVersion


def _can_retrain(user):
    return user.is_superuser or user.groups.filter(name=ADMINISTRATOR).exists()


@gate_staff_required
def insights_page(request):
    snap = insights.snapshot()
    queue = (
        VisitorVisit.objects.filter(status=VisitorVisit.Status.PENDING)
        .select_related("prediction")
        .order_by("prediction__approval_probability", "-created_at")
    )
    page = paginate(request, queue)
    traffic_model = ml.active_version(ModelVersion.Kind.TRAFFIC)
    visit_model = ml.active_version(ModelVersion.Kind.VISIT_RISK)
    charts = {
        "today": insights.today_series(),
        "daily": data.daily_entries(14),
        "importance": {
            "traffic": (traffic_model.feature_importance if traffic_model else [])[:8],
            "visit": (visit_model.feature_importance if visit_model else [])[:8],
        },
    }
    return render(request, "analytics/insights.html", {
        "section": "insights",
        "snap": snap,
        "traffic_model": traffic_model,
        "visit_model": visit_model,
        "history": ModelVersion.objects.all()[:8],
        "queue": page.object_list,
        "page_obj": page,
        "charts_json": json.dumps(charts),
        "can_retrain": _can_retrain(request.user),
    })


@gate_staff_required
@require_POST
def retrain(request):
    if not _can_retrain(request.user):
        messages.error(request, "Only an administrator can retrain the models.")
        return redirect("dashboard:insights")
    try:
        result = training.run(log=lambda *_: None)
    except Exception as exc:
        messages.error(request, f"Training failed: {exc}")
    else:
        messages.success(
            request,
            f"Trained traffic v{result['traffic'].version} and visit risk v{result['visit_risk'].version}.",
        )
    return redirect("dashboard:insights")
