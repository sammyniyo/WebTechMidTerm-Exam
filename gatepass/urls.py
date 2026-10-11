from django.urls import path

from . import views

app_name = "gatepass"

urlpatterns = [
    path("visitor/register/", views.visitor_register, name="visitor_register"),
]
