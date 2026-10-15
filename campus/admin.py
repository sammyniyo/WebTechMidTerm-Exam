
from django.contrib import admin
from .models import Building, Office


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(Office)
class OfficeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "building",
        "floor",
        "room_number",
        "is_active",
    )
    search_fields = ("name", "room_number", "building__name")
    list_filter = ("building", "floor", "is_active")
