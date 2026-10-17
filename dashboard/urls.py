from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("visitors/", views.visitor_list, name="visitor_list"),
    path("visitors/<str:reference>/", views.visit_detail, name="visit_detail"),
    path("log/", views.gate_log, name="gate_log"),
]
