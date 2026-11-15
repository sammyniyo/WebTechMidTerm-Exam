from django.contrib import admin

from .models import HourlyTraffic, ModelVersion, TrafficForecast, VisitPrediction, WeatherHour


@admin.register(ModelVersion)
class ModelVersionAdmin(admin.ModelAdmin):
    list_display = ("kind", "version", "algorithm", "data_source", "train_rows", "is_active", "trained_at")
    list_filter = ("kind", "is_active")


@admin.register(VisitPrediction)
class VisitPredictionAdmin(admin.ModelAdmin):
    list_display = ("visit", "approval_probability", "risk_level", "actual_outcome", "predicted_at")
    list_filter = ("risk_level", "actual_outcome")


@admin.register(HourlyTraffic)
class HourlyTrafficAdmin(admin.ModelAdmin):
    list_display = ("hour_start", "entries", "visitors", "rain_mm", "source")
    list_filter = ("source",)


admin.site.register(TrafficForecast)
admin.site.register(WeatherHour)
