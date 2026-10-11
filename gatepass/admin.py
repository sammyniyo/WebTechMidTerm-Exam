from django.contrib import admin

from .models import VisitorVisit


@admin.register(VisitorVisit)
class VisitorVisitAdmin(admin.ModelAdmin):
    list_display = (
        "reference_number",
        "first_name",
        "last_name",
        "destination",
        "status",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("reference_number", "first_name", "last_name", "phone", "organization")
    readonly_fields = ("reference_number", "created_at")
