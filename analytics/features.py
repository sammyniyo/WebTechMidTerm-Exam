"""Feature engineering shared by training, the prediction API, and live scoring.

Both models take plain dicts and use scikit-learn's ``DictVectorizer``, so
the same function builds features for a training row and for a visitor who
registered a second ago.
"""

import math
from datetime import date

from django.utils import timezone

TERM_BREAKS = (
    ((12, 20), (12, 31)),
    ((1, 1), (1, 6)),
    ((4, 24), (5, 5)),
    ((8, 8), (8, 31)),
)

ORGANIZATION_KEYWORDS = (
    ("government", ("ministry", "minister", "rra", "rdb", "police", "district", "government", "nesa", "hec", "embassy")),
    ("education", ("school", "university", "college", "academy", "institute", "auca", "library")),
    ("delivery", ("courier", "delivery", "dhl", "express", "post", "parcel")),
    ("family", ("parent", "family", "guardian", "relative", "mother", "father")),
    ("business", ("ltd", "company", "bank", "plc", "inc", "group", "telecom", "mtn", "airtel", "enterprise", "co.")),
)

DESTINATION_KEYWORDS = (
    ("academic", ("dean", "faculty", "department", "lecturer", "library", "academic", "research")),
    ("registry", ("registrar", "admission", "records", "transcript")),
    ("finance", ("finance", "account", "bursar", "cashier", "business office")),
    ("student_services", ("student", "chaplain", "counsel", "health", "clinic", "nurse", "sport")),
    ("administration", ("vice", "chancellor", "president", "human resource", "hr", "admin", "ict", "it ")),
)


def in_term(day: date) -> int:
    for (m1, d1), (m2, d2) in TERM_BREAKS:
        if (m1, d1) <= (day.month, day.day) <= (m2, d2):
            return 0
    return 1


def traffic_features(hour_start, temperature_c, rain_mm):
    local = timezone.localtime(hour_start)
    return {
        "hour": local.hour,
        "hour_sin": math.sin(local.hour / 24 * 2 * math.pi),
        "hour_cos": math.cos(local.hour / 24 * 2 * math.pi),
        "weekday": local.weekday(),
        "is_saturday": int(local.weekday() == 5),
        "is_sunday": int(local.weekday() == 6),
        "month": local.month,
        "in_term": in_term(local.date()),
        "temperature_c": float(temperature_c if temperature_c is not None else 21.0),
        "rain_mm": float(rain_mm or 0.0),
    }


def _match(text, table, default):
    text = f" {(text or '').lower()} "
    for label, words in table:
        if any(word in text for word in words):
            return label
    return default


def organization_type(name):
    return _match(name, ORGANIZATION_KEYWORDS, "individual")


def destination_group(name):
    return _match(name, DESTINATION_KEYWORDS, "other")


def visit_features(*, created_at, destination, organization, email, host_name, purpose,
                   prior_visits=0, prior_rejections=0):
    local = timezone.localtime(created_at) if timezone.is_aware(created_at) else created_at
    hour = local.hour
    return {
        "hour": hour,
        "weekday": local.weekday(),
        "is_saturday": int(local.weekday() == 5),
        "out_of_hours": int(hour < 7 or hour >= 18),
        "has_email": int(bool((email or "").strip())),
        "has_host": int(bool((host_name or "").strip())),
        "purpose_words": min(len((purpose or "").split()), 30),
        "prior_visits": min(int(prior_visits), 10),
        "prior_rejections": min(int(prior_rejections), 5),
        "destination_group": destination_group(destination),
        "organization_type": organization_type(organization),
    }


def visit_signals(features):
    """Plain-language notes the desk sees next to a score.

    These restate the inputs the model weighs most. They are not a per-visit
    attribution of the model's output.
    """
    notes = []
    if features["prior_rejections"]:
        notes.append(("negative", f"{features['prior_rejections']} earlier visit(s) rejected"))
    if not features["has_host"]:
        notes.append(("negative", "No host named"))
    if features["out_of_hours"]:
        notes.append(("negative", "Registered outside office hours"))
    if features["is_saturday"]:
        notes.append(("negative", "Sabbath registration"))
    if features["purpose_words"] == 0:
        notes.append(("negative", "No reason given"))
    if not features["has_email"]:
        notes.append(("neutral", "No email address"))
    if features["prior_visits"] and not features["prior_rejections"]:
        notes.append(("positive", f"Returning visitor ({features['prior_visits']} earlier visit(s))"))
    if features["organization_type"] in ("government", "education"):
        notes.append(("positive", f"{features['organization_type'].title()} organization"))
    if features["has_host"] and features["purpose_words"] >= 3:
        notes.append(("positive", "Host and reason both given"))
    return [{"tone": tone, "text": text} for tone, text in notes]
