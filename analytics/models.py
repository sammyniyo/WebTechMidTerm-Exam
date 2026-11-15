"""Tables for the machine-learning layer.

``HourlyTraffic`` is the training history for the traffic model. Live rows are
rebuilt from ``GateEvent`` and ``CheckIn``; synthetic rows fill the past so a
fresh install has something to learn from. ``source`` keeps the two apart.
"""

from django.db import models


class HourlyTraffic(models.Model):
    class Source(models.TextChoices):
        LIVE = "live", "Live gate records"
        SYNTHETIC = "synthetic", "Synthetic history"

    hour_start = models.DateTimeField(unique=True)
    entries = models.PositiveIntegerField(default=0)
    visitors = models.PositiveIntegerField(default=0)
    temperature_c = models.FloatField(null=True, blank=True)
    rain_mm = models.FloatField(null=True, blank=True)
    source = models.CharField(max_length=12, choices=Source.choices)

    class Meta:
        ordering = ["hour_start"]
        verbose_name_plural = "hourly traffic"

    def __str__(self):
        return f"{self.hour_start:%Y-%m-%d %H:00} · {self.entries} entries"


class WeatherHour(models.Model):
    class Source(models.TextChoices):
        OPEN_METEO = "open-meteo", "Open-Meteo API"
        ESTIMATE = "estimate", "Seasonal estimate"

    hour_start = models.DateTimeField(unique=True)
    temperature_c = models.FloatField()
    rain_mm = models.FloatField()
    source = models.CharField(max_length=12, choices=Source.choices)
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["hour_start"]

    def __str__(self):
        return f"{self.hour_start:%Y-%m-%d %H:00} · {self.temperature_c}°C · {self.rain_mm} mm"


class ModelVersion(models.Model):
    class Kind(models.TextChoices):
        TRAFFIC = "traffic", "Gate traffic forecaster"
        VISIT_RISK = "visit_risk", "Visit approval classifier"

    kind = models.CharField(max_length=16, choices=Kind.choices)
    version = models.PositiveIntegerField()
    algorithm = models.CharField(max_length=80)
    artifact = models.CharField(max_length=255, help_text="File name inside ML_MODEL_DIR.")
    data_source = models.CharField(max_length=40)
    train_rows = models.PositiveIntegerField()
    test_rows = models.PositiveIntegerField()
    metrics = models.JSONField(default=dict)
    feature_importance = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    trained_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-trained_at"]
        constraints = [
            models.UniqueConstraint(fields=["kind", "version"], name="unique_model_version"),
        ]

    def __str__(self):
        return f"{self.get_kind_display()} v{self.version}"


class TrafficForecast(models.Model):
    hour_start = models.DateTimeField(unique=True)
    predicted_entries = models.FloatField()
    temperature_c = models.FloatField(null=True, blank=True)
    rain_mm = models.FloatField(null=True, blank=True)
    model_version = models.ForeignKey(ModelVersion, on_delete=models.CASCADE, related_name="forecasts")
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["hour_start"]

    def __str__(self):
        return f"{self.hour_start:%Y-%m-%d %H:00} · {self.predicted_entries:.1f}"


class VisitPrediction(models.Model):
    class Risk(models.TextChoices):
        LOW = "low", "Low risk"
        MEDIUM = "medium", "Review"
        HIGH = "high", "High risk"

    class Outcome(models.TextChoices):
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    visit = models.OneToOneField(
        "gatepass.VisitorVisit", on_delete=models.CASCADE, related_name="prediction"
    )
    approval_probability = models.FloatField()
    risk_level = models.CharField(max_length=8, choices=Risk.choices)
    signals = models.JSONField(default=list)
    model_version = models.ForeignKey(ModelVersion, on_delete=models.CASCADE, related_name="visit_predictions")
    predicted_at = models.DateTimeField(auto_now_add=True)
    actual_outcome = models.CharField(max_length=8, choices=Outcome.choices, blank=True)

    class Meta:
        ordering = ["-predicted_at"]

    def __str__(self):
        return f"{self.visit.reference_number} · {self.approval_probability:.0%}"

    @property
    def predicted_outcome(self):
        return self.Outcome.APPROVED if self.approval_probability >= 0.5 else self.Outcome.REJECTED

    @property
    def matched(self):
        if not self.actual_outcome:
            return None
        return self.actual_outcome == self.predicted_outcome

    @property
    def percent(self):
        return round(self.approval_probability * 100)

    @property
    def badge(self):
        return {"low": "success", "medium": "warning", "high": "danger"}[self.risk_level]
