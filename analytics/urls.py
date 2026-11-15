from django.urls import path

from . import api

app_name = "analytics"

urlpatterns = [
    path("datasets/traffic/", api.traffic_dataset, name="traffic_dataset"),
    path("datasets/visits/", api.visit_dataset, name="visit_dataset"),
    path("models/", api.models, name="models"),
    path("forecast/", api.forecast, name="forecast"),
    path("predict/traffic/", api.predict_traffic, name="predict_traffic"),
    path("predict/visit/", api.predict_visit, name="predict_visit"),
    path("live/", api.live, name="live"),
]
