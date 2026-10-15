
from django.urls import path
from . import api, views

app_name = "campus"

urlpatterns = [
    # JSON API
    path("api/buildings/", api.buildings, name="api_buildings"),
    path(
        "api/buildings/<int:pk>/",
        api.building_detail,
        name="api_building_detail",
    ),
    path("api/offices/", api.offices, name="api_offices"),
    path(
        "api/offices/<int:pk>/",
        api.office_detail,
        name="api_office_detail",
    ),

    # Public directory
    path("offices/", views.office_directory, name="office_directory"),
    path("offices/<int:pk>/", views.office_detail, name="office_detail"),

    # Staff office management
    path("campus/offices/manage/", views.office_list, name="office_list"),
    path(
        "campus/offices/create/",
        views.office_create,
        name="office_create",
    ),
    path(
        "campus/offices/<int:pk>/edit/",
        views.office_update,
        name="office_update",
    ),
    path(
        "campus/offices/<int:pk>/delete/",
        views.office_delete,
        name="office_delete",
    ),

    # Building list
    path("campus/buildings/", views.building_list, name="building_list"),
]
