from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="accounts/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("verify/", views.verify_member, name="verify"),
    path("api/accounts/verify/", views.verify_api, name="verify_api"),
    path("api/accounts/members/", views.member_list_api, name="member_list_api"),
    path(
        "api/accounts/members/<str:campus_id>/",
        views.member_detail_api,
        name="member_detail_api",
    ),
]
