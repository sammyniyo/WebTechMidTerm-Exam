from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import gate_staff_required
from .models import GateEvent, VisitorVisit
from .forms import VisitorRegistrationForm


def visitor_register(request):
    visit = None
    if request.method == "POST":
        form = VisitorRegistrationForm(request.POST)
        if form.is_valid():
            visit = form.save()
    else:
        form = VisitorRegistrationForm()
    return render(
        request,
        "gatepass/register.html",
        {"form": form, "visit": visit},
    )


def visitor_pass(request, reference):
    visit = get_object_or_404(VisitorVisit, reference_number=reference)
    return render(
        request,
        "gatepass/pass.html",
        {"visit": visit, "is_expired": visit.valid_until <= timezone.now()},
    )


@gate_staff_required
@require_POST
def review_visit(request, reference):
    visit = get_object_or_404(VisitorVisit, reference_number=reference)
    decision = request.POST.get("decision")
    if visit.status != VisitorVisit.Status.PENDING:
        messages.error(request, "Only pending visits can be reviewed.")
    elif decision == "approve":
        visit.status = VisitorVisit.Status.APPROVED
        visit.save(update_fields=["status"])
        messages.success(request, "Visit approved.")
    elif decision == "reject":
        visit.status = VisitorVisit.Status.REJECTED
        visit.save(update_fields=["status"])
        messages.success(request, "Visit rejected.")
    else:
        messages.error(request, "Choose approve or reject.")
    return redirect("dashboard:visit_detail", reference=visit.reference_number)


@gate_staff_required
@require_POST
def record_gate_event(request, reference):
    visit = get_object_or_404(VisitorVisit, reference_number=reference)
    event_type = request.POST.get("event_type")
    if event_type not in GateEvent.EventType.values:
        messages.error(request, "Choose entry or exit.")
        return redirect("dashboard:visit_detail", reference=visit.reference_number)
    now = timezone.now()
    allowed_entry = (
        visit.status == VisitorVisit.Status.APPROVED
        and visit.valid_until > now
    )
    allowed_exit = visit.status == VisitorVisit.Status.CHECKED_IN
    accepted = (
        event_type == GateEvent.EventType.ENTRY and allowed_entry
    ) or (event_type == GateEvent.EventType.EXIT and allowed_exit)

    GateEvent.objects.create(
        visit=visit,
        event_type=event_type,
        officer=request.user,
        outcome=GateEvent.Outcome.ACCEPTED if accepted else GateEvent.Outcome.REJECTED,
    )

    if accepted and event_type == GateEvent.EventType.ENTRY:
        visit.status = VisitorVisit.Status.CHECKED_IN
        visit.save(update_fields=["status"])
        messages.success(request, "Entry recorded.")
    elif accepted:
        visit.status = VisitorVisit.Status.COMPLETED
        visit.save(update_fields=["status"])
        messages.success(request, "Exit recorded. Visit completed.")
    else:
        messages.error(request, "This visit is not eligible for that gate action.")
    return redirect("dashboard:visit_detail", reference=visit.reference_number)
