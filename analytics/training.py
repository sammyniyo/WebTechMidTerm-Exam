"""The full training run used by `train_models` and the dashboard Retrain button."""

from collections import Counter
from datetime import timedelta

from django.utils import timezone

from gatepass.models import VisitorVisit

from . import data, ml, synthetic, weather
from .client import fetch
from .models import HourlyTraffic


def seed_history(days=180, seed=42):
    """Replace synthetic traffic rows with ``days`` of fresh history ending yesterday."""
    end = timezone.localdate()
    start = end - timedelta(days=days)
    weather.fetch_history(start, end - timedelta(days=1))
    HourlyTraffic.objects.filter(source=HourlyTraffic.Source.SYNTHETIC).delete()
    live_hours = set(HourlyTraffic.objects.values_list("hour_start", flat=True))
    rows = [
        HourlyTraffic(source=HourlyTraffic.Source.SYNTHETIC, **row)
        for row in synthetic.hourly_traffic(start, days, seed=seed)
        if row["hour_start"] not in live_hours
    ]
    HourlyTraffic.objects.bulk_create(rows, batch_size=500)
    return len(rows)


def run(source="api", api_url=None, token=None, min_real_visits=300, log=print):
    """Train both models. ``source`` is "api" or "synthetic"."""
    results = {}

    # Traffic
    if source == "synthetic":
        start = timezone.localdate() - timedelta(days=180)
        rows = list(synthetic.hourly_traffic(start, 180))
        label = "synthetic (in memory)"
    else:
        if not api_url:
            synced = data.sync_live_traffic()
            log(f"Synced {synced} live gate hours into the history table.")
            if not HourlyTraffic.objects.filter(source=HourlyTraffic.Source.SYNTHETIC).exists():
                log(f"No history yet; seeded {seed_history()} synthetic hours.")
        payload = fetch("/api/analytics/datasets/traffic/", {"days": 365}, api_url, token)
        rows = payload["results"]
        mix = Counter(row["source"] for row in rows)
        label = f"API: {mix.get('live', 0)} live + {mix.get('synthetic', 0)} synthetic hours"
    log(f"Traffic training rows: {len(rows)} ({label})")
    results["traffic"] = ml.train_traffic(rows, label)

    # Visits: real decided visits from the API, topped up with synthetic
    # examples while the real history is still small.
    real = [] if source == "synthetic" else fetch("/api/analytics/datasets/visits/", None, api_url, token)["results"]
    extra = 1500 if len(real) < min_real_visits else 0
    rows = real + [{"features": f, "approved": y} for f, y in synthetic.labelled_visits(extra)]
    label = "synthetic (in memory)" if source == "synthetic" else f"API: {len(real)} real + {extra} synthetic visits"
    log(f"Visit training rows: {len(rows)} ({label})")
    results["visit_risk"] = ml.train_visit_risk(rows, label)

    ml.refresh_forecast()
    rescored = 0
    for visit in VisitorVisit.objects.filter(status=VisitorVisit.Status.PENDING):
        ml.score_visit(visit)
        rescored += 1
    log(f"Forecast refreshed; {rescored} pending visit(s) scored.")
    return results
