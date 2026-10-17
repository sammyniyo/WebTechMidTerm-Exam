from django.urls import path

from . import views

app_name = "gatepass"

urlpatterns = [
    path("visitor/register/", views.visitor_register, name="visitor_register"),
    path("visitor/pass/<str:reference>/", views.visitor_pass, name="visitor_pass"),
    path("visitor/<str:reference>/review/", views.review_visit, name="review_visit"),
    path("visitor/<str:reference>/gate/", views.record_gate_event, name="record_gate_event"),
]
