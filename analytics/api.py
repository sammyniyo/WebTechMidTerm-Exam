"""JSON API for the analytics app.

Data:        GET  /api/analytics/datasets/traffic/?days=180
             GET  /api/analytics/datasets/visits/
Models:      GET  /api/analytics/models/
Predictions: GET  /api/analytics/forecast/
             GET  /api/analytics/predict/traffic/?date=2026-11-16
             POST /api/analytics/predict/visit/   {"organization": ..., ...}
Live:        GET  /api/analytics/live/

Send either a desk staff session or `Authorization: Token <ANALYTICS_API_TOKEN>`.
"""

import hmac
import json
from datetime import date, datetime, timedelta
from functools import wraps

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from accounts.roles import user_can_manage_gate

from . import data, insights, ml
from .features import visit_features
from .models import ModelVersion, TrafficForecast
from gatepass.models import VisitorVisit


def _json(payload, status=200):
    return JsonResponse(payload, status=status, encoder=DjangoJSONEncoder, safe=False)


def _token_ok(request):
    expected = settings.ANALYTICS_API_TOKEN
    header = request.headers.get("Authorization", "")
    if not expected or not header.startswith("Token "):
        return False
    return hmac.compare_digest(header[6:].strip(), expected)


def api_view(*methods):
    def decorator(view):
        @csrf_exempt
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.method not in methods:
                response = _json({"error": "Method not allowed."}, 405)
                response["Allow"] = ", ".join(methods)
                return response
            allowed = (
                getattr(request, "_analytics_internal", False)
                or _token_ok(request)
                or user_can_manage_gate(request.user)
            )
            if not allowed:
                return _json({"error": "Sign in as desk staff or send an API token."}, 401)
            try:
                return view(request, *args, **kwargs)
            except ml.ModelNotReady as exc:
                return _json({"error": str(exc)}, 503)
        return wrapped
    return decorator


@api_view("GET")
def traffic_dataset(request):
    try:
        days = max(1, min(int(request.GET.get("days", 180)), 730))
    except ValueError:
        return _json({"error": "days must be a number."}, 400)
    rows = data.traffic_rows(days)
    return _json({"count": len(rows), "days": days, "results": rows})


@api_view("GET")
def visit_dataset(request):
    rows = data.visit_rows()
    return _json({"count": len(rows), "results": rows})


def _model_data(record):
    return {
        "kind": record.kind,
        "name": record.get_kind_display(),
        "version": record.version,
        "algorithm": record.algorithm,
        "data_source": record.data_source,
        "train_rows": record.train_rows,
        "test_rows": record.test_rows,
        "metrics": record.metrics,
        "feature_importance": record.feature_importance,
        "is_active": record.is_active,
        "trained_at": record.trained_at,
    }


@api_view("GET")
def models(request):
    return _json({"results": [_model_data(r) for r in ModelVersion.objects.all()[:20]]})


@api_view("GET")
def forecast(request):
    ml.ensure_forecast()
    start = timezone.localtime().replace(minute=0, second=0, microsecond=0)
    rows = TrafficForecast.objects.filter(hour_start__gte=start)[:48]
    return _json({
        "results": [
            {
                "hour_start": timezone.localtime(r.hour_start),
                "predicted_entries": r.predicted_entries,
                "officers_needed": ml.officers_needed(r.predicted_entries),
                "temperature_c": r.temperature_c,
                "rain_mm": r.rain_mm,
                "model_version": r.model_version.version,
            }
            for r in rows
        ]
    })


@api_view("GET")
def predict_traffic(request):
    raw = request.GET.get("date") or timezone.localdate().isoformat()
    try:
        day = date.fromisoformat(raw)
    except ValueError:
        return _json({"error": "date must look like 2026-11-16."}, 400)
    start = timezone.make_aware(datetime.combine(day, datetime.min.time()))
    hours = [start + timedelta(hours=i) for i in range(24)]
    record, values = ml.predict_hours(hours)
    return _json({
        "date": day,
        "model_version": record.version,
        "total": round(sum(values)),
        "results": [
            {"hour": f"{h:%H}:00", "predicted_entries": v, "officers_needed": ml.officers_needed(v)}
            for h, v in zip(hours, values)
        ],
    })


@api_view("POST")
def predict_visit(request):
    try:
        body = json.loads(request.body.decode() or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _json({"error": "Send a JSON object."}, 400)
    if not isinstance(body, dict):
        return _json({"error": "Send a JSON object."}, 400)
    if not str(body.get("organization", "")).strip() or not str(body.get("destination", "")).strip():
        return _json({"error": "organization and destination are required."}, 400)
    created_at = timezone.now()
    if body.get("created_at"):
        try:
            created_at = datetime.fromisoformat(body["created_at"])
            if timezone.is_naive(created_at):
                created_at = timezone.make_aware(created_at)
        except ValueError:
            return _json({"error": "created_at must be ISO 8601."}, 400)
    prior = rejected = 0
    if body.get("phone"):
        earlier = VisitorVisit.objects.filter(phone=body["phone"])
        prior, rejected = earlier.count(), earlier.filter(status=VisitorVisit.Status.REJECTED).count()
    features = visit_features(
        created_at=created_at,
        destination=body.get("destination"),
        organization=body.get("organization"),
        email=body.get("email", ""),
        host_name=body.get("host_name", ""),
        purpose=body.get("purpose", ""),
        prior_visits=body.get("prior_visits", prior),
        prior_rejections=body.get("prior_rejections", rejected),
    )
    record, probability, risk, signals = ml.predict_visit(features)
    return _json({
        "approval_probability": probability,
        "predicted_outcome": "approved" if probability >= 0.5 else "rejected",
        "risk_level": risk,
        "signals": signals,
        "features": features,
        "model_version": record.version,
    })


@api_view("GET")
def live(request):
    return _json(insights.snapshot())
