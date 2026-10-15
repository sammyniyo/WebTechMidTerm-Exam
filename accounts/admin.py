from django.contrib import admin

from .models import CampusMember, CheckIn, StaffProfile, StudentProfile


class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    extra = 0
    max_num = 1


class StaffProfileInline(admin.StackedInline):
    model = StaffProfile
    extra = 0
    max_num = 1


@admin.register(CampusMember)
class CampusMemberAdmin(admin.ModelAdmin):
    list_display = (
        "campus_id",
        "full_name",
        "member_type",
        "status",
        "department_code",
    )
    list_filter = ("member_type", "status", "department_code")
    search_fields = ("campus_id", "full_name", "email", "account_code")
    inlines = [StudentProfileInline, StaffProfileInline]


@admin.register(CheckIn)
class CheckInAdmin(admin.ModelAdmin):
    list_display = ("member", "checked_in_at")
    search_fields = ("member__campus_id", "member__full_name")
