from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import gate_staff_required
from accounts.roles import user_can_manage_gate
from . import qr
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
    from campus.models import Office

    office = (
        Office.objects.filter(is_active=True, name__iexact=visit.destination)
        .select_related("building")
        .first()
    )
    return render(
        request,
        "gatepass/pass.html",
        {
            "visit": visit,
            "office": office,
            "is_expired": visit.valid_until <= timezone.now(),
        },
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
    return _desk_next(request, visit.reference_number)


@gate_staff_required
@require_POST
def record_gate_event(request, reference):
    visit = get_object_or_404(VisitorVisit, reference_number=reference)
    event_type = request.POST.get("event_type")
    if event_type not in GateEvent.EventType.values:
        messages.error(request, "Choose entry or exit.")
        return _desk_next(request, visit.reference_number)
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
    return _desk_next(request, visit.reference_number)


def _desk_next(request, reference):
    target = request.POST.get("next") or ""
    if target.startswith("/dashboard/") and not target.startswith("//"):
        return redirect(target)
    return redirect("dashboard:visit_detail", reference=reference)


def _svg_response(content, filename, download):
    response = HttpResponse(content, content_type="image/svg+xml")
    response["Cache-Control"] = "private, max-age=3600"
    if download:
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def visitor_qr(request, reference):
    """QR image for one visitor pass. ``?download=1`` saves it as a file."""
    visit = get_object_or_404(VisitorVisit, reference_number=reference)
    target = qr.absolute_url(request, reverse("gatepass:visitor_scan", args=[visit.reference_number]))
    return _svg_response(qr.svg(target), f"{visit.reference_number}.svg", request.GET.get("download"))


def visitor_scan(request, reference):
    """Where a pass QR leads: the desk page for officers, the pass for everyone else."""
    visit = get_object_or_404(VisitorVisit, reference_number=reference)
    if user_can_manage_gate(request.user):
        return redirect("dashboard:visit_detail", reference=visit.reference_number)
    return redirect("gatepass:visitor_pass", reference=visit.reference_number)


def gate_qr(request):
    """QR image for the gate poster. It opens the visitor registration form."""
    target = qr.absolute_url(request, reverse("gatepass:visitor_register"))
    return _svg_response(qr.svg(target), "auca-gate-check-in.svg", request.GET.get("download"))


@gate_staff_required
def gate_poster(request):
    return render(request, "gatepass/gate_poster.html", {
        "section": "gate_qr",
        "register_url": qr.absolute_url(request, reverse("gatepass:visitor_register")),
    })
