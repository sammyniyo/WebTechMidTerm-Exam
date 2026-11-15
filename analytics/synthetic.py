"""Synthetic training data with realistic, learnable patterns.

No real personal data is generated. Patterns built in on purpose:

* Gate traffic peaks at 07-08 (classes start), 12-13 (lunch), and 17-18
  (evening programme); the Sabbath (Saturday) is quiet; term breaks cut
  traffic by about two thirds; rain keeps people away.
* Visits are more likely to be approved with a named host, a stated reason,
  a known organization, and a clean history; out-of-hours, Sabbath, and
  repeat-rejected visitors are more likely to be turned away.
"""

import math
import random
from datetime import datetime, timedelta

import numpy as np
from django.utils import timezone

from . import weather
from .features import in_term

HOURLY_PROFILE = [0, 0, 0, 0, 0, 2, 14, 62, 78, 44, 30, 34, 46, 40, 30, 28, 34, 48, 36, 18, 9, 4, 1, 0]
WEEKDAY_FACTOR = [1.0, 1.05, 1.0, 1.0, 0.72, 0.1, 0.55]  # Monday .. Sunday
VISITOR_SHARE = [0, 0, 0, 0, 0, 0, .02, .05, .1, .2, .24, .22, .12, .16, .2, .18, .1, .05, .03, .02, 0, 0, 0, 0]

DESTINATIONS = [
    "Registrar Office", "Admissions Office", "Finance Office", "Dean of Students",
    "Faculty of Information Technology", "Library", "Health Centre", "Human Resources",
    "ICT Department", "Chaplaincy", "Business Office", "Research Office",
]
ORGANIZATIONS = [
    ("Ministry of Education", 1.0), ("Rwanda Revenue Authority", 0.6), ("Gasabo District", 0.5),
    ("Kigali Public Library", 0.7), ("University of Rwanda", 0.8), ("Green Hills Academy", 0.6),
    ("Bank of Kigali", 0.9), ("MTN Rwanda", 0.7), ("Inyange Industries Ltd", 0.6), ("Rwanda Build Group", 0.5),
    ("Parent", 1.4), ("Family", 0.6), ("DHL Express", 0.5), ("Courier", 0.6),
    ("Self", 1.2), ("Independent", 0.7), ("Freelancer", 0.5), ("None", 0.4),
]
ORG_EFFECT = {"government": 0.9, "education": 0.7, "business": 0.35, "family": 0.4,
              "delivery": -0.4, "individual": -0.7}
DEST_EFFECT = {"registry": 0.5, "academic": 0.3, "student_services": 0.3, "finance": 0.0,
               "administration": -0.3, "other": 0.0}
PURPOSES = [
    "", "", "Meeting", "Collect a transcript", "Deliver a parcel to the office",
    "Pay school fees for my child", "Interview for a job", "Courtesy visit",
    "Meeting with the dean about a partnership", "Submit admission documents",
    "Visit a sick relative at the health centre", "Repair the network equipment",
]


def hourly_traffic(start_date, days, seed=42):
    """Yield dicts of synthetic hourly traffic, using stored weather when known."""
    rng = np.random.default_rng(seed)
    tz = timezone.get_current_timezone()
    hours = [
        timezone.make_aware(datetime.combine(start_date + timedelta(days=d), datetime.min.time()) + timedelta(hours=h), tz)
        for d in range(days) for h in range(24)
    ]
    conditions = weather.weather_for(hours)
    for hour_start in hours:
        local = timezone.localtime(hour_start)
        temp, rain, _source = conditions[hour_start]
        term = 1.0 if in_term(local.date()) else 0.35
        rain_factor = math.exp(-0.3 * min(rain, 10))
        heat = 1.0 - 0.015 * max(temp - 27, 0)
        expected = HOURLY_PROFILE[local.hour] * WEEKDAY_FACTOR[local.weekday()] * term * rain_factor * heat
        entries = int(rng.poisson(expected)) if expected > 0 else 0
        visitors = int(rng.binomial(entries, VISITOR_SHARE[local.hour])) if entries else 0
        yield {
            "hour_start": hour_start,
            "entries": entries,
            "visitors": visitors,
            "temperature_c": temp,
            "rain_mm": rain,
        }


def _organization(rng):
    names, weights = zip(*ORGANIZATIONS)
    return rng.choices(names, weights=weights)[0]


def visitor(rng, when):
    """One synthetic visitor registration (no label)."""
    first = rng.choice(["Aline", "Eric", "Grace", "David", "Diane", "Jean", "Keza", "Patrick", "Amina", "Claude", "Ange", "Yves"])
    last = rng.choice(["Uwase", "Habimana", "Mukamana", "Mugisha", "Uwimana", "Hakizimana", "Niyonzima", "Ingabire", "Kaneza", "Nshuti"])
    has_host = rng.random() < 0.72
    return {
        "first_name": first,
        "last_name": last,
        "phone": "+2507" + "".join(rng.choice("0123456789") for _ in range(8)),
        "email": f"{first.lower()}.{last.lower()}@example.com" if rng.random() < 0.6 else "",
        "organization": _organization(rng),
        "destination": rng.choice(DESTINATIONS),
        "host_name": rng.choice(["Eric Habimana", "Grace Mukamana", "Aline Ingabire", "Dr. Jean Nshuti"]) if has_host else "",
        "purpose": rng.choice(PURPOSES),
        "created_at": when,
    }


def approval_probability(features):
    """The ground-truth rule the synthetic labels are drawn from."""
    logit = 1.6
    logit += 0.9 if features["has_host"] else -0.9
    logit += 0.35 if features["has_email"] else -0.25
    logit += -0.9 if features["purpose_words"] == 0 else min(features["purpose_words"], 8) * 0.06
    logit += -1.6 if features["out_of_hours"] else 0
    logit += -1.2 if features["is_saturday"] else 0
    logit += 0.3 * min(features["prior_visits"], 3)
    logit += -1.8 * features["prior_rejections"]
    logit += ORG_EFFECT[features["organization_type"]]
    logit += DEST_EFFECT[features["destination_group"]]
    return 1 / (1 + math.exp(-logit))


def _registration_time(rng, now):
    day = now - timedelta(days=rng.randint(1, 180))
    hour = rng.choices(range(24), weights=[0, 0, 0, 0, 0, 1, 3, 8, 12, 14, 14, 12, 8, 10, 11, 10, 8, 5, 3, 2, 1, 1, 0, 0])[0]
    return day.replace(hour=hour, minute=rng.randint(0, 59), second=0, microsecond=0)


def labelled_visits(count, seed=7):
    """Return ``count`` (features, approved) pairs for training."""
    from .features import visit_features

    rng = random.Random(seed)
    now = timezone.localtime()
    rows = []
    for _ in range(count):
        raw = visitor(rng, _registration_time(rng, now))
        history = rng.choices([0, 1, 2, 3, 4], weights=[60, 18, 10, 7, 5])[0]
        rejections = sum(rng.random() < 0.15 for _ in range(history))
        features = visit_features(
            created_at=raw["created_at"], destination=raw["destination"], organization=raw["organization"],
            email=raw["email"], host_name=raw["host_name"], purpose=raw["purpose"],
            prior_visits=history, prior_rejections=rejections,
        )
        rows.append((features, int(rng.random() < approval_probability(features))))
    return rows
