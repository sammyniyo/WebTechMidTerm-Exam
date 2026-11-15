"""Train, save, load, and run the two scikit-learn models.

* Traffic forecaster: ``RandomForestRegressor`` predicting accepted gate
  entries for one hour from the calendar and the weather.
* Visit approval classifier: ``RandomForestClassifier`` predicting whether
  the desk will approve a new visitor registration.

Each training run becomes a ``ModelVersion`` row plus a joblib file in
``settings.ML_MODEL_DIR``. Only the newest version of each kind is active.
"""

import logging
import math
from datetime import datetime, timedelta

import joblib
import numpy as np
import sklearn
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.feature_extraction import DictVectorizer
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from . import weather
from .features import traffic_features, visit_signals
from .models import ModelVersion, TrafficForecast, VisitPrediction

log = logging.getLogger(__name__)

LOW_RISK_AT = 0.75   # approval probability at or above this is low risk
HIGH_RISK_BELOW = 0.5
ENTRIES_PER_OFFICER = 40


class ModelNotReady(Exception):
    """No trained model of this kind is active yet."""


# ---------------------------------------------------------------- saving

def _model_dir():
    path = settings.ML_MODEL_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def _importance(pipeline):
    names = pipeline.named_steps["vectorize"].get_feature_names_out()
    weights = pipeline.named_steps["model"].feature_importances_
    grouped = {}
    for name, weight in zip(names, weights):
        key = name.split("=")[0]
        grouped[key] = grouped.get(key, 0.0) + float(weight)
    ranked = sorted(grouped.items(), key=lambda item: item[1], reverse=True)
    return [{"feature": key, "weight": round(weight, 4)} for key, weight in ranked]


@transaction.atomic
def _register(kind, pipeline, algorithm, data_source, train_rows, test_rows, metrics):
    latest = ModelVersion.objects.filter(kind=kind).order_by("-version").first()
    version = (latest.version + 1) if latest else 1
    artifact = f"{kind}_v{version}.joblib"
    joblib.dump(
        {"pipeline": pipeline, "kind": kind, "version": version, "sklearn": sklearn.__version__},
        _model_dir() / artifact,
    )
    ModelVersion.objects.filter(kind=kind, is_active=True).update(is_active=False)
    record = ModelVersion.objects.create(
        kind=kind,
        version=version,
        algorithm=algorithm,
        artifact=artifact,
        data_source=data_source,
        train_rows=train_rows,
        test_rows=test_rows,
        metrics=metrics,
        feature_importance=_importance(pipeline),
        is_active=True,
    )
    _cache.pop(kind, None)
    return record


_cache = {}


def active_version(kind):
    return ModelVersion.objects.filter(kind=kind, is_active=True).order_by("-version").first()


def load(kind):
    """Return (ModelVersion, pipeline) for the active model, cached per version."""
    record = active_version(kind)
    if record is None:
        raise ModelNotReady(f"No {kind} model has been trained yet.")
    cached = _cache.get(kind)
    if cached and cached[0].pk == record.pk:
        return cached
    path = _model_dir() / record.artifact
    if not path.exists():
        raise ModelNotReady(f"Model file {record.artifact} is missing. Run `python manage.py train_models`.")
    bundle = joblib.load(path)
    _cache[kind] = (record, bundle["pipeline"])
    return _cache[kind]


# ---------------------------------------------------------------- traffic

def _traffic_matrix(rows):
    features, targets, stamps = [], [], []
    for row in rows:
        stamp = row["hour_start"]
        if isinstance(stamp, str):
            stamp = datetime.fromisoformat(stamp)
        features.append(traffic_features(stamp, row.get("temperature_c"), row.get("rain_mm")))
        targets.append(row["entries"])
        stamps.append(stamp)
    return features, np.array(targets, dtype=float), stamps


def train_traffic(rows, data_source):
    if len(rows) < 24 * 14:
        raise ValueError(f"Need at least 14 days of hourly traffic to train; got {len(rows)} rows.")
    features, targets, stamps = _traffic_matrix(rows)
    order = np.argsort(np.array([s.timestamp() for s in stamps]))
    features = [features[i] for i in order]
    targets = targets[order]
    split = int(len(features) * 0.8)  # chronological: test on the most recent 20%
    x_train, x_test = features[:split], features[split:]
    y_train, y_test = targets[:split], targets[split:]

    pipeline = Pipeline([
        ("vectorize", DictVectorizer(sparse=False)),
        ("model", RandomForestRegressor(n_estimators=150, min_samples_leaf=3, random_state=42, n_jobs=-1)),
    ])
    pipeline.fit(x_train, y_train)
    predicted = np.clip(pipeline.predict(x_test), 0, None)

    # Baseline: the average for the same weekday and hour in the training data.
    buckets = {}
    for row, value in zip(x_train, y_train):
        buckets.setdefault((row["weekday"], row["hour"]), []).append(value)
    baseline = np.array([np.mean(buckets.get((row["weekday"], row["hour"]), [0])) for row in x_test])

    mae = mean_absolute_error(y_test, predicted)
    baseline_mae = mean_absolute_error(y_test, baseline)
    metrics = {
        "mae": round(float(mae), 2),
        "rmse": round(float(math.sqrt(mean_squared_error(y_test, predicted))), 2),
        "r2": round(float(r2_score(y_test, predicted)), 3),
        "baseline_mae": round(float(baseline_mae), 2),
        "improvement_pct": round(float((baseline_mae - mae) / baseline_mae * 100), 1) if baseline_mae else 0.0,
        "test_period": f"{timezone.localtime(stamps[order[split]]):%d %b %Y} – {timezone.localtime(stamps[order[-1]]):%d %b %Y}",
    }
    pipeline.fit(features, targets)  # refit on everything before deployment
    return _register(
        ModelVersion.Kind.TRAFFIC, pipeline, "RandomForestRegressor (150 trees)",
        data_source, split, len(features) - split, metrics,
    )


def predict_hours(hour_starts, conditions=None):
    """Predicted entries for each hour. ``conditions`` maps hour -> (temp, rain, source)."""
    record, pipeline = load(ModelVersion.Kind.TRAFFIC)
    hour_starts = list(hour_starts)
    conditions = conditions or weather.weather_for(hour_starts)
    rows = [traffic_features(h, conditions[h][0], conditions[h][1]) for h in hour_starts]
    values = np.clip(pipeline.predict(rows), 0, None) if rows else []
    return record, [round(float(v), 1) for v in values]


def refresh_forecast(hours=36, fetch_weather=True):
    """Predict the next ``hours`` hours (from the start of today) and store them."""
    start = timezone.localtime().replace(minute=0, second=0, microsecond=0, hour=0)
    end_hour = timezone.localtime().replace(minute=0, second=0, microsecond=0) + timedelta(hours=hours)
    count = int((end_hour - start).total_seconds() // 3600)
    hour_starts = [start + timedelta(hours=i) for i in range(count)]
    if fetch_weather:
        weather.fetch_forecast(days=3)
    conditions = weather.weather_for(hour_starts)
    record, values = predict_hours(hour_starts, conditions)
    for hour_start, value in zip(hour_starts, values):
        TrafficForecast.objects.update_or_create(
            hour_start=hour_start,
            defaults={
                "predicted_entries": value,
                "temperature_c": conditions[hour_start][0],
                "rain_mm": conditions[hour_start][1],
                "model_version": record,
            },
        )
    return record, len(hour_starts)


def ensure_forecast(max_age_minutes=30):
    """Refresh the stored forecast when it is stale. Never raises."""
    try:
        record = active_version(ModelVersion.Kind.TRAFFIC)
        if record is None:
            return False
        horizon = timezone.localtime().replace(minute=0, second=0, microsecond=0) + timedelta(hours=24)
        latest = TrafficForecast.objects.order_by("-created_at").first()
        fresh = (
            latest is not None
            and latest.model_version_id == record.pk
            and latest.created_at > timezone.now() - timedelta(minutes=max_age_minutes)
            and TrafficForecast.objects.filter(hour_start__gte=horizon).exists()
        )
        if not fresh:
            refresh_forecast()
        return True
    except Exception:
        log.exception("Could not refresh the traffic forecast.")
        return False


def officers_needed(predicted_entries):
    return max(1, math.ceil(predicted_entries / ENTRIES_PER_OFFICER))


# ---------------------------------------------------------------- visits

def train_visit_risk(rows, data_source):
    if len(rows) < 60:
        raise ValueError(f"Need at least 60 decided visits to train; got {len(rows)}.")
    features = [row["features"] for row in rows]
    labels = np.array([row["approved"] for row in rows])
    if len(set(labels)) < 2:
        raise ValueError("Training data needs both approved and rejected visits.")
    x_train, x_test, y_train, y_test = train_test_split(
        features, labels, test_size=0.25, random_state=42, stratify=labels
    )
    pipeline = Pipeline([
        ("vectorize", DictVectorizer(sparse=False)),
        ("model", RandomForestClassifier(
            n_estimators=200, max_depth=8, min_samples_leaf=4,
            random_state=42, n_jobs=-1,
        )),
    ])
    pipeline.fit(x_train, y_train)
    probability = pipeline.predict_proba(x_test)[:, 1]
    predicted = (probability >= 0.5).astype(int)
    majority = max(np.mean(y_test), 1 - np.mean(y_test))
    tn, fp, fn, tp = confusion_matrix(y_test, predicted, labels=[0, 1]).ravel()
    metrics = {
        "accuracy": round(float(accuracy_score(y_test, predicted)), 3),
        "precision": round(float(precision_score(y_test, predicted, zero_division=0)), 3),
        "recall": round(float(recall_score(y_test, predicted, zero_division=0)), 3),
        "f1": round(float(f1_score(y_test, predicted, zero_division=0)), 3),
        "roc_auc": round(float(roc_auc_score(y_test, probability)), 3),
        "baseline_accuracy": round(float(majority), 3),
        "approval_rate": round(float(np.mean(labels)), 3),
        "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }
    pipeline.fit(features, labels)
    return _register(
        ModelVersion.Kind.VISIT_RISK, pipeline, "RandomForestClassifier (200 trees)",
        data_source, len(x_train), len(x_test), metrics,
    )


def risk_level(probability):
    if probability >= LOW_RISK_AT:
        return VisitPrediction.Risk.LOW
    if probability >= HIGH_RISK_BELOW:
        return VisitPrediction.Risk.MEDIUM
    return VisitPrediction.Risk.HIGH


def predict_visit(features):
    """Score one feature dict. Returns (ModelVersion, probability, risk, signals)."""
    record, pipeline = load(ModelVersion.Kind.VISIT_RISK)
    probability = float(pipeline.predict_proba([features])[0][1])
    return record, round(probability, 4), risk_level(probability), visit_signals(features)


def score_visit(visit):
    """Create or refresh the stored prediction for a ``VisitorVisit``."""
    from .data import features_for

    record, probability, risk, signals = predict_visit(features_for(visit))
    prediction, _ = VisitPrediction.objects.update_or_create(
        visit=visit,
        defaults={
            "approval_probability": probability,
            "risk_level": risk,
            "signals": signals,
            "model_version": record,
        },
    )
    return prediction
