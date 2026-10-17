from datetime import timedelta

from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone

from accounts.decorators import gate_staff_required
from accounts.models import CheckIn
from campus.models import Office
from gatepass.models import GateEvent, VisitorVisit

BADGES = {
    "pending": "warning",
    "approved": "success",
    "checked_in": "info",
    "rejected": "danger",
    "completed": "success",
    "accepted": "success",
}


def _initials(name):
    parts = [part for part in (name or "").split() if part]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return ((name or "?")[:2]).upper()


def _today_bounds():
    start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


def _visit_row(visit):
    return {
        "initials": _initials(visit.full_name),
        "name": visit.full_name,
        "reference": visit.reference_number,
        "organization": visit.organization,
        "destination": visit.destination,
        "host": visit.host_name,
        "arrived": timezone.localtime(visit.created_at).strftime("%d %b %Y, %H:%M"),
        "badge": BADGES.get(visit.status, "info"),
        "status_label": visit.get_status_display(),
        "phone": visit.phone,
        "email": visit.email,
        "purpose": visit.purpose,
        "valid_until": timezone.localtime(visit.valid_until).strftime("%d %b %Y, %H:%M"),
    }


def _event_row(event):
    if event.visit_id:
        person = event.visit.full_name
        kind = "Visitor"
    else:
        person = event.member.full_name
        kind = event.member.get_member_type_display()
    return {
        "initials": _initials(person),
        "person": person,
        "kind": kind,
        "event": event.get_event_type_display(),
        "time": timezone.localtime(event.occurred_at).strftime("%H:%M"),
        "badge": BADGES.get(event.outcome, "info"),
        "result_label": event.get_outcome_display(),
        "officer": event.officer.get_username(),
        "when": event.occurred_at,
    }


def _checkin_row(check_in):
    return {
        "initials": _initials(check_in.member.full_name),
        "person": check_in.member.full_name,
        "kind": check_in.member.get_member_type_display(),
        "event": "Entry",
        "time": timezone.localtime(check_in.checked_in_at).strftime("%H:%M"),
        "badge": "success",
        "result_label": "Accepted",
        "officer": "Check-in",
        "when": check_in.checked_in_at,
    }


def _stats():
    start, end = _today_bounds()
    visitors = VisitorVisit.objects.filter(created_at__gte=start, created_at__lt=end).count()
    pending = VisitorVisit.objects.filter(status=VisitorVisit.Status.PENDING).count()
    gate_entries = GateEvent.objects.filter(
        event_type=GateEvent.EventType.ENTRY,
        outcome=GateEvent.Outcome.ACCEPTED,
        occurred_at__gte=start,
        occurred_at__lt=end,
    ).count()
    member_entries = CheckIn.objects.filter(checked_in_at__gte=start, checked_in_at__lt=end).count()
    offices = Office.objects.filter(is_active=True, building__is_active=True).count()
    return [
        {"key": "visitors", "label": "Visitors today", "value": visitors, "hint": "Registered today"},
        {"key": "pending", "label": "Pending", "value": pending, "hint": "Waiting for the desk"},
        {"key": "entries", "label": "Entries today", "value": gate_entries + member_entries, "hint": "Accepted at the gate"},
        {"key": "offices", "label": "Active offices", "value": offices, "hint": "Open for visitors"},
    ], {
        "visitors_today": visitors,
        "pending_visits": pending,
        "entries_today": gate_entries + member_entries,
        "active_offices": offices,
    }


def _mix():
    order = (
        (VisitorVisit.Status.PENDING, "Pending"),
        (VisitorVisit.Status.APPROVED, "Approved"),
        (VisitorVisit.Status.CHECKED_IN, "Checked in"),
        (VisitorVisit.Status.REJECTED, "Rejected"),
    )
    counts = []
    for key, label in order:
        counts.append(
            {
                "key": key,
                "label": label,
                "count": VisitorVisit.objects.filter(status=key).count(),
                "badge": BADGES[key],
            }
        )
    return counts


def _trend():
    start, _end = _today_bounds()
    hours = list(range(8, 19))
    counts = {hour: 0 for hour in hours}
    events = GateEvent.objects.filter(
        event_type=GateEvent.EventType.ENTRY,
        outcome=GateEvent.Outcome.ACCEPTED,
        occurred_at__gte=start,
    )
    checkins = CheckIn.objects.filter(checked_in_at__gte=start)
    for event in events:
        hour = timezone.localtime(event.occurred_at).hour
        if hour in counts:
            counts[hour] += 1
    for check_in in checkins:
        hour = timezone.localtime(check_in.checked_in_at).hour
        if hour in counts:
            counts[hour] += 1
    peak = max(counts.values()) or 1
    bars = []
    for hour in hours:
        count = counts[hour]
        bars.append(
            {
                "label": f"{hour:02d}",
                "count": count,
                "height": round(count * 100 / peak) if count else 8,
                "empty": count == 0,
            }
        )
    return bars


@gate_staff_required
def home(request):
    stats, totals = _stats()
    start, _end = _today_bounds()
    visits = [_visit_row(visit) for visit in VisitorVisit.objects.all()[:8]]
    gate_rows = [
        _event_row(event)
        for event in GateEvent.objects.select_related("visit", "member", "officer").filter(occurred_at__gte=start)[:12]
    ]
    check_rows = [
        _checkin_row(check_in)
        for check_in in CheckIn.objects.select_related("member").filter(checked_in_at__gte=start)[:12]
    ]
    activity = sorted(gate_rows + check_rows, key=lambda row: row["when"], reverse=True)[:8]
    return render(
        request,
        "dashboard/index.html",
        {
            "section": "overview",
            "stats": stats,
            "visitors": visits[:4],
            "events": activity,
            "mix": _mix(),
            "trend": _trend(),
            **totals,
        },
    )


@gate_staff_required
def visitor_list(request):
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
            | Q(organization__icontains=query)
        )
    return render(
        request,
        "dashboard/visitors.html",
        {
            "section": "visitors",
            "visitors": [_visit_row(visit) for visit in visits[:100]],
            "query": query,
        },
    )


@gate_staff_required
def visit_detail(request, reference):
    visit = (
        VisitorVisit.objects.prefetch_related("gate_events__officer")
        .filter(reference_number=reference)
        .first()
    )
    return render(
        request,
        "dashboard/visit_detail.html",
        {"section": "visitors", "visit": visit},
        status=200 if visit else 404,
    )


@gate_staff_required
def gate_log(request):
    query = request.GET.get("q", "").strip()
    events = GateEvent.objects.select_related("visit", "member", "officer")
    checkins = CheckIn.objects.select_related("member")
    if query:
        events = events.filter(
            Q(visit__reference_number__icontains=query)
            | Q(visit__first_name__icontains=query)
            | Q(visit__last_name__icontains=query)
            | Q(member__campus_id__icontains=query)
            | Q(member__full_name__icontains=query)
            | Q(officer__username__icontains=query)
        )
        checkins = checkins.filter(
            Q(member__campus_id__icontains=query) | Q(member__full_name__icontains=query)
        )
    rows = [_event_row(event) for event in events[:150]]
    rows.extend(_checkin_row(check_in) for check_in in checkins[:150])
    rows.sort(key=lambda row: row["when"], reverse=True)
    return render(
        request,
        "dashboard/gate_log.html",
        {"section": "log", "events": rows[:150], "query": query},
    )
