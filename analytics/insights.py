"""Numbers for the dashboard and the live API, computed in one place."""

from datetime import timedelta

from django.utils import timezone

from gatepass.models import VisitorVisit

from . import data, ml
from .models import ModelVersion, TrafficForecast, VisitPrediction


def _forecast_map(start, hours):
    rows = TrafficForecast.objects.filter(hour_start__gte=start, hour_start__lt=start + timedelta(hours=hours))
    return {timezone.localtime(row.hour_start): row for row in rows}


def today_series():
    """Actual and predicted entries for every hour today and tomorrow."""
    start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    forecast = _forecast_map(start, 48)
    actual = data.hourly_series(start, 24)
    hours = [start + timedelta(hours=i) for i in range(48)]
    return {
        "labels": [f"{h:%H}:00" for h in hours[:24]],
        "actual": actual,
        "predicted": [round(forecast[h].predicted_entries, 1) if h in forecast else None for h in hours[:24]],
        "tomorrow": [round(forecast[h].predicted_entries, 1) if h in forecast else None for h in hours[24:]],
        "rain": [round(forecast[h].rain_mm or 0, 1) if h in forecast else None for h in hours[:24]],
        "temperature": [forecast[h].temperature_c if h in forecast else None for h in hours[:24]],
        "tomorrow_label": hours[24].strftime("%A %d %b"),
    }


def _alert(actual, predicted, hour):
    """Compare the last finished hour with its forecast."""
    if hour == 0 or predicted[hour - 1] is None:
        return None
    seen, expected = actual[hour - 1], predicted[hour - 1]
    gap = seen - expected
    if abs(gap) >= max(5, expected * 0.5):
        direction = "busier" if gap > 0 else "quieter"
        return {
            "tone": "warning" if gap > 0 else "info",
            "text": f"{hour - 1:02d}:00 was {direction} than forecast: {seen} entries against {expected:.0f} expected.",
        }
    return None


def snapshot():
    ml.ensure_forecast()
    now = timezone.localtime()
    series = today_series()
    actual, predicted = series["actual"], series["predicted"]
    hour = now.hour
    has_forecast = any(value is not None for value in predicted)

    traffic = None
    if has_forecast:
        upcoming = [(h, predicted[h]) for h in range(hour + 1, 24) if predicted[h] is not None]
        label_day = "today"
        if not upcoming or max(v for _, v in upcoming) < 1:
            upcoming = [(h, v) for h, v in enumerate(series["tomorrow"]) if v is not None]
            label_day = "tomorrow"
        peak_hour, peak_value = max(upcoming, key=lambda item: item[1]) if upcoming else (hour, 0)
        next_value = predicted[hour + 1] if hour < 23 else (series["tomorrow"][0] or 0)
        traffic = {
            "actual_so_far": sum(actual[: hour + 1]),
            "expected_so_far": round(sum(v or 0 for v in predicted[: hour + 1])),
            "expected_today": round(sum(v or 0 for v in predicted)),
            "expected_rest_of_day": round(sum(v or 0 for v in predicted[hour + 1:])),
            "next_hour": {"label": f"{(hour + 1) % 24:02d}:00", "entries": round(next_value or 0)},
            "peak": {
                "label": f"{peak_hour:02d}:00",
                "day": label_day,
                "entries": round(peak_value),
                "officers": ml.officers_needed(peak_value),
            },
            "weather": {
                "temperature_c": series["temperature"][hour],
                "rain_mm": series["rain"][hour],
            },
            "alert": _alert(actual, predicted, hour),
        }

    pending = VisitorVisit.objects.filter(status=VisitorVisit.Status.PENDING)
    decided = VisitPrediction.objects.exclude(actual_outcome="")
    matched = sum(1 for p in decided.only("approval_probability", "actual_outcome") if p.matched)
    recent = VisitPrediction.objects.select_related("visit").order_by("-predicted_at")[:6]
    return {
        "generated_at": now.isoformat(),
        "clock": now.strftime("%H:%M:%S"),
        "models_ready": {
            "traffic": ml.active_version(ModelVersion.Kind.TRAFFIC) is not None,
            "visit_risk": ml.active_version(ModelVersion.Kind.VISIT_RISK) is not None,
        },
        "traffic": traffic,
        "visits": {
            "pending": pending.count(),
            "high_risk_pending": pending.filter(prediction__risk_level=VisitPrediction.Risk.HIGH).count(),
            "unscored_pending": pending.filter(prediction__isnull=True).count(),
            "live_accuracy": {
                "decided": decided.count(),
                "matched": matched,
                "rate": round(matched / decided.count(), 3) if decided.count() else None,
            },
        },
        "recent_predictions": [
            {
                "reference": p.visit.reference_number,
                "name": p.visit.full_name,
                "destination": p.visit.destination,
                "probability": p.approval_probability,
                "percent": p.percent,
                "risk": p.risk_level,
                "risk_label": p.get_risk_level_display(),
                "badge": p.badge,
                "status": p.visit.get_status_display(),
                "time": timezone.localtime(p.predicted_at).strftime("%H:%M"),
            }
            for p in recent
        ],
    }
