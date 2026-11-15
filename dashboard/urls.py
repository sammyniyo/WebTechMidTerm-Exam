from django.urls import path

from accounts import desk
from analytics import views as analytics_views
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("visitors/", views.visitor_list, name="visitor_list"),
    path("visits/", views.visitor_list, name="visit_list"),
    path("visitors/<str:reference>/", views.visit_detail, name="visit_detail"),
    path("visits/<str:reference>/", views.visit_detail),
    path("people/", desk.member_list, name="member_list"),
    path("people/new/", desk.member_create, name="member_create"),
    path("people/<int:pk>/edit/", desk.member_update, name="member_edit"),
    path("people/<int:pk>/delete/", desk.member_delete, name="member_delete"),
    path("check-ins/", views.check_ins, name="check_ins"),
    path("check-ins/<int:pk>/approve/", views.approve_check_in, name="approve_check_in"),
    path("check-ins/<int:pk>/checkout/", views.checkout_check_in, name="checkout_check_in"),
    path("insights/", analytics_views.insights_page, name="insights"),
    path("insights/retrain/", analytics_views.retrain, name="retrain"),
    path("log/", views.gate_log, name="gate_log"),
    path("gate-log/", views.gate_log),
]
