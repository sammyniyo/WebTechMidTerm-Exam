"""Turn gate records into training datasets.

The API in ``analytics/api.py`` serves these rows, and training reads them
back through that API, so a remote service could train on the same data.
"""

from collections import Counter, defaultdict
from datetime import timedelta

from django.utils import timezone

from accounts.models import CheckIn
from gatepass.models import GateEvent, VisitorVisit

from . import weather
from .features import visit_features
from .models import HourlyTraffic

APPROVED_STATES = (
    VisitorVisit.Status.APPROVED,
    VisitorVisit.Status.CHECKED_IN,
    VisitorVisit.Status.COMPLETED,
)


def hour_floor(moment):
    local = timezone.localtime(moment)
    return local.replace(minute=0, second=0, microsecond=0)


def live_counts(start, end):
    """Accepted entries and visitor registrations per local hour in [start, end)."""
    entries = Counter()
    visitors = Counter()
    gate = (
        GateEvent.objects.filter(
            event_type=GateEvent.EventType.ENTRY,
            outcome=GateEvent.Outcome.ACCEPTED,
            occurred_at__gte=start,
            occurred_at__lt=end,
        ).values_list("occurred_at", flat=True)
    )
    for moment in gate:
        entries[hour_floor(moment)] += 1
    members = CheckIn.objects.filter(approved_at__gte=start, approved_at__lt=end).values_list("approved_at", flat=True)
    for moment in members:
        entries[hour_floor(moment)] += 1
    for moment in VisitorVisit.objects.filter(created_at__gte=start, created_at__lt=end).values_list("created_at", flat=True):
        visitors[hour_floor(moment)] += 1
    return entries, visitors


def sync_live_traffic(days=365):
    """Copy real gate activity into ``HourlyTraffic``.

    Only finished hours with recorded activity are written. Those rows replace
    any synthetic row for the same hour.
    """
    end = hour_floor(timezone.now())
    start = end - timedelta(days=days)
    entries, visitors = live_counts(start, end)
    hours = sorted(set(entries) | set(visitors))
    conditions = weather.weather_for(hours)
    for hour_start in hours:
        temp, rain, _source = conditions[hour_start]
        HourlyTraffic.objects.update_or_create(
            hour_start=hour_start,
            defaults={
                "entries": entries[hour_start],
                "visitors": visitors[hour_start],
                "temperature_c": temp,
                "rain_mm": rain,
                "source": HourlyTraffic.Source.LIVE,
            },
        )
    return len(hours)


def traffic_rows(days=180):
    since = timezone.now() - timedelta(days=days)
    rows = HourlyTraffic.objects.filter(hour_start__gte=since).order_by("hour_start")
    return [
        {
            "hour_start": timezone.localtime(row.hour_start).isoformat(),
            "entries": row.entries,
            "visitors": row.visitors,
            "temperature_c": row.temperature_c,
            "rain_mm": row.rain_mm,
            "source": row.source,
        }
        for row in rows
    ]


def visit_history():
    """Each visit with how many earlier visits and rejections share its phone."""
    seen = defaultdict(int)
    rejected = defaultdict(int)
    for visit in VisitorVisit.objects.order_by("created_at"):
        yield visit, seen[visit.phone], rejected[visit.phone]
        seen[visit.phone] += 1
        if visit.status == VisitorVisit.Status.REJECTED:
            rejected[visit.phone] += 1


def history_for(visit):
    earlier = VisitorVisit.objects.filter(phone=visit.phone, created_at__lt=visit.created_at).exclude(pk=visit.pk)
    return earlier.count(), earlier.filter(status=VisitorVisit.Status.REJECTED).count()


def features_for(visit, prior_visits=None, prior_rejections=None):
    if prior_visits is None:
        prior_visits, prior_rejections = history_for(visit)
    return visit_features(
        created_at=visit.created_at,
        destination=visit.destination,
        organization=visit.organization,
        email=visit.email,
        host_name=visit.host_name,
        purpose=visit.purpose,
        prior_visits=prior_visits,
        prior_rejections=prior_rejections,
    )


def visit_rows():
    """Decided visits only: approved (1) or rejected (0)."""
    rows = []
    for visit, prior, prior_rejected in visit_history():
        if visit.status == VisitorVisit.Status.PENDING:
            continue
        rows.append(
            {
                "reference": visit.reference_number,
                "features": features_for(visit, prior, prior_rejected),
                "approved": int(visit.status in APPROVED_STATES),
            }
        )
    return rows


def hourly_series(start, hours):
    """Actual accepted entries for ``hours`` consecutive hours from ``start``."""
    end = start + timedelta(hours=hours)
    entries, _visitors = live_counts(start, end)
    return [entries[start + timedelta(hours=i)] for i in range(hours)]


def daily_entries(days=14):
    today = timezone.localdate()
    start = hour_floor(timezone.now()).replace(hour=0) - timedelta(days=days - 1)
    entries, _ = live_counts(start, start + timedelta(days=days))
    totals = Counter()
    for hour_start, count in entries.items():
        totals[hour_start.date()] += count
    stored = (
        HourlyTraffic.objects.filter(hour_start__gte=start, source=HourlyTraffic.Source.SYNTHETIC)
        .values_list("hour_start", "entries")
    )
    synthetic = Counter()
    for hour_start, count in stored:
        synthetic[timezone.localtime(hour_start).date()] += count
    result = []
    for offset in range(days):
        day = today - timedelta(days=days - 1 - offset)
        live = totals.get(day, 0)
        result.append({"date": day.isoformat(), "label": day.strftime("%d %b"), "live": live, "synthetic": synthetic.get(day, 0)})
    return result
