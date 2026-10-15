from django.contrib import admin

from .models import GateEvent, VisitorVisit


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


@admin.register(GateEvent)
class GateEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "visit", "member", "occurred_at", "officer", "outcome")
    list_filter = ("event_type", "outcome", "occurred_at")
    search_fields = ("visit__reference_number", "visit__first_name", "visit__last_name", "member__campus_id", "officer__username")
    readonly_fields = ("occurred_at",)
