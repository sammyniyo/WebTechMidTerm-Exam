from django.apps import apps
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from accounts.decorators import gate_staff_required
from gatepass.models import GateEvent, VisitorVisit


@gate_staff_required
def home(request):
    today = timezone.localdate()
    offices_model = _office_model()
    active_offices = (
        offices_model.objects.filter(is_active=True).count() if offices_model else 0
    )
    context = {
        "visitors_today": VisitorVisit.objects.filter(created_at__date=today).count(),
        "pending_visits": VisitorVisit.objects.filter(
            status=VisitorVisit.Status.PENDING
        ).count(),
        "entries_today": GateEvent.objects.filter(
            event_type=GateEvent.EventType.ENTRY,
            outcome=GateEvent.Outcome.ACCEPTED,
            occurred_at__date=today,
        ).count(),
        "active_offices": active_offices,
        "recent_visits": VisitorVisit.objects.all()[:8],
        "recent_events": GateEvent.objects.select_related(
            "visit", "member", "officer"
        )[:8],
    }
    return render(request, "dashboard/index.html", context)


@gate_staff_required
def visit_list(request):
    query = request.GET.get("q", "").strip()
    visits = VisitorVisit.objects.all()
    if query:
        visits = visits.filter(
            Q(reference_number__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(phone__icontains=query)
            | Q(destination__icontains=query)
            | Q(host_name__icontains=query)
        )
    return render(
        request,
        "dashboard/visits.html",
        {"visits": visits[:100], "query": query},
    )


@gate_staff_required
def visit_detail(request, reference):
    visit = get_object_or_404(
        VisitorVisit.objects.prefetch_related("gate_events"),
        reference_number=reference,
    )
    return render(request, "dashboard/visit_detail.html", {"visit": visit})


@gate_staff_required
def gate_log(request):
    query = request.GET.get("q", "").strip()
    events = GateEvent.objects.select_related("visit", "member", "officer")
    if query:
        events = events.filter(
            Q(visit__reference_number__icontains=query)
            | Q(visit__first_name__icontains=query)
            | Q(visit__last_name__icontains=query)
            | Q(member__campus_id__icontains=query)
            | Q(member__full_name__icontains=query)
            | Q(officer__username__icontains=query)
        )
    return render(
        request,
        "dashboard/gate_log.html",
        {"events": events[:150], "query": query},
    )


def _office_model():
    try:
        return apps.get_model("campus", "Office")
    except LookupError:
        return None
