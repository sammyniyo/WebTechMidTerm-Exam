from django.urls import path

from accounts import desk
from analytics import views as analytics_views
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("visits/", views.visit_list, name="visit_list"),
    path("visits/<str:reference>/", views.visit_detail, name="visit_detail"),
    path("gate-log/", views.gate_log, name="gate_log"),
]
