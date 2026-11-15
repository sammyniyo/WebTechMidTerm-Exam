"""Kigali weather from the Open-Meteo API (https://open-meteo.com).

Open-Meteo is free and needs no key. Past hours come from the archive API and
upcoming hours from the forecast API. When the network is down, or the API is
disabled in settings, a seasonal estimate keeps training and forecasting
working. Each row records which of the two it came from.
"""

import json
import logging
import math
import random
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from .models import WeatherHour

log = logging.getLogger(__name__)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
BACKOFF_KEY = "analytics:weather-backoff"

# Kigali has two rainy seasons: March to May and September to December.
MONTHLY_RAIN_CHANCE = {1: .12, 2: .14, 3: .22, 4: .30, 5: .22, 6: .04,
                       7: .03, 8: .06, 9: .14, 10: .20, 11: .24, 12: .16}


def estimate(hour_start):
    """Deterministic seasonal weather for one hour (no network)."""
    local = timezone.localtime(hour_start)
    rng = random.Random(local.strftime("%Y%m%d%H"))
    temp = 20.5 + 5.5 * math.sin((local.hour - 9) / 24 * 2 * math.pi) + rng.uniform(-1.2, 1.2)
    rain = 0.0
    if rng.random() < MONTHLY_RAIN_CHANCE[local.month] * (1.6 if 13 <= local.hour <= 19 else 0.7):
        rain = round(rng.expovariate(1 / 2.5), 1)
    return round(temp, 1), rain


def _get(url, params):
    if not settings.WEATHER_API_ENABLED or cache.get(BACKOFF_KEY):
        return None
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(f"{url}?{query}", headers={"User-Agent": "smart-gate-pass/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return json.loads(response.read().decode())
    except Exception as exc:  # network, HTTP, or JSON errors
        log.warning("Open-Meteo request failed (%s); using seasonal estimate.", exc)
        cache.set(BACKOFF_KEY, True, 15 * 60)
        return None


def _store(payload):
    hourly = (payload or {}).get("hourly") or {}
    tz = timezone.get_current_timezone()
    incoming = {}
    for stamp, temp, rain in zip(hourly.get("time") or [], hourly.get("temperature_2m") or [], hourly.get("precipitation") or []):
        if temp is not None and rain is not None:
            incoming[timezone.make_aware(datetime.fromisoformat(stamp), tz)] = (temp, rain)
    if not incoming:
        return 0
    existing = {row.hour_start: row for row in WeatherHour.objects.filter(hour_start__in=list(incoming))}
    create, update = [], []
    for hour_start, (temp, rain) in incoming.items():
        row = existing.get(hour_start)
        if row is None:
            create.append(WeatherHour(hour_start=hour_start, temperature_c=temp, rain_mm=rain, source=WeatherHour.Source.OPEN_METEO))
        else:
            row.temperature_c, row.rain_mm, row.source = temp, rain, WeatherHour.Source.OPEN_METEO
            update.append(row)
    WeatherHour.objects.bulk_create(create, batch_size=500)
    WeatherHour.objects.bulk_update(update, ["temperature_c", "rain_mm", "source"], batch_size=500)
    return len(incoming)


def _params(**extra):
    return {
        "latitude": settings.CAMPUS_LATITUDE,
        "longitude": settings.CAMPUS_LONGITUDE,
        "hourly": "temperature_2m,precipitation",
        "timezone": settings.TIME_ZONE,
        **extra,
    }


def fetch_history(start_date, end_date):
    """Store archived hourly weather between two dates. Returns rows saved."""
    # The archive lags a few days behind; the forecast API covers the gap.
    latest_archive = timezone.localdate() - timedelta(days=5)
    end = min(end_date, latest_archive)
    saved = 0
    if start_date <= end:
        saved += _store(_get(ARCHIVE_URL, _params(start_date=start_date.isoformat(), end_date=end.isoformat()))) or 0
    saved += _store(_get(FORECAST_URL, _params(past_days=7, forecast_days=1))) or 0
    return saved


def fetch_forecast(days=2):
    """Store forecast weather for the coming days. Returns rows saved."""
    return _store(_get(FORECAST_URL, _params(forecast_days=days))) or 0


def weather_for(hour_starts):
    """Map each hour to (temperature, rain, source), filling gaps with estimates."""
    hour_starts = list(hour_starts)
    if not hour_starts:
        return {}
    known = {
        row.hour_start: (row.temperature_c, row.rain_mm, row.source)
        for row in WeatherHour.objects.filter(hour_start__gte=min(hour_starts), hour_start__lte=max(hour_starts))
    }
    result = {}
    for hour_start in hour_starts:
        if hour_start in known:
            result[hour_start] = known[hour_start]
        else:
            temp, rain = estimate(hour_start)
            result[hour_start] = (temp, rain, WeatherHour.Source.ESTIMATE)
    return result
