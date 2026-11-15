from django.urls import path

from . import views

app_name = "gatepass"

urlpatterns = [
    path("visitor/register/", views.visitor_register, name="visitor_register"),
    path("visitor/pass/<str:reference>/", views.visitor_pass, name="visitor_pass"),
    path("visitor/pass/<str:reference>/qr.svg", views.visitor_qr, name="visitor_qr"),
    path("visitor/scan/<str:reference>/", views.visitor_scan, name="visitor_scan"),
    path("visitor/gate-qr.svg", views.gate_qr, name="gate_qr"),
    path("visitor/gate-poster/", views.gate_poster, name="gate_poster"),
    path("visitor/<str:reference>/review/", views.review_visit, name="review_visit"),
    path("visitor/<str:reference>/gate/", views.record_gate_event, name="record_gate_event"),
]
