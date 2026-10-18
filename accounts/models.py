from django.core.exceptions import ValidationError
from django.db import models


class CampusMember(models.Model):
    """Shared identity for a student or a staff member.

    ``campus_id`` is the public ID printed on the campus card (the ``id``
    field in the source record). ``record`` primary key is what other apps
    should store in a foreign key.
    """

    class MemberType(models.TextChoices):
        STUDENT = "student", "Student"
        STAFF = "staff", "Staff"

    class Sex(models.TextChoices):
        MALE = "M", "Male"
        FEMALE = "F", "Female"

    class MaritalStatus(models.TextChoices):
        SINGLE = "S", "Single"
        MARRIED = "M", "Married"
        DIVORCED = "D", "Divorced"
        WIDOWED = "W", "Widowed"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"
        SUSPENDED = "SUSPENDED", "Suspended"
        ON_LEAVE = "ON_LEAVE", "On leave"
        GRADUATED = "GRADUATED", "Graduated"

    campus_id = models.CharField(max_length=32, unique=True)
    internal_id = models.PositiveIntegerField(unique=True, null=True, blank=True)
    member_type = models.CharField(max_length=16, choices=MemberType.choices)
    full_name = models.CharField(max_length=150)
    sex = models.CharField(max_length=1, choices=Sex.choices, blank=True)
    marital_status = models.CharField(
        max_length=1, choices=MaritalStatus.choices, blank=True
    )
    birth_date = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=64, blank=True)
    national_id = models.CharField(max_length=32, unique=True, null=True, blank=True)
    actual_address = models.CharField(max_length=255, blank=True)
    religion = models.CharField(max_length=64, blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE
    )
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    department_code = models.CharField(max_length=16, blank=True)
    account_code = models.CharField(max_length=32, blank=True)
    disability_status = models.BooleanField(default=False)
    disability_details = models.TextField(blank=True)
    profile_complete = models.BooleanField(default=False)
    missing_profile_fields = models.JSONField(default=list, blank=True)
    has_profile_picture = models.BooleanField(default=False)
    profile_picture_updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.full_name} ({self.campus_id})"

    @property
    def is_active_member(self):
        return self.status == self.Status.ACTIVE


class StudentProfile(models.Model):
    class AcademicLevel(models.TextChoices):
        UNDERGRADUATE = "UNDERGRADUATE", "Undergraduate"
        GRADUATE = "GRADUATE", "Graduate"

    class StudyMode(models.TextChoices):
        DAY = "DAY", "Day"
        EVENING = "EVENING", "Evening"
        WEEKEND = "WEEKEND", "Weekend"
        MASTERS = "MASTERS", "Masters"

    member = models.OneToOneField(
        CampusMember, on_delete=models.CASCADE, related_name="student_profile"
    )
    academic_level = models.CharField(max_length=32, choices=AcademicLevel.choices)
    study_mode = models.CharField(max_length=32, choices=StudyMode.choices)
    admitted_term_id = models.CharField(max_length=16, blank=True)
    high_school_name = models.CharField(max_length=150, blank=True)
    high_school_combination = models.CharField(max_length=32, blank=True)
    high_school_location = models.CharField(max_length=120, blank=True)
    high_school_id = models.CharField(max_length=32, null=True, blank=True)
    secondary_school_aggregate_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )

    def __str__(self):
        return f"Student profile for {self.member.campus_id}"

    def clean(self):
        if self.member_id and self.member.member_type != CampusMember.MemberType.STUDENT:
            raise ValidationError("Student details can only be saved on a student.")


class StaffProfile(models.Model):
    class Category(models.TextChoices):
        ACADEMIC = "ACADEMIC", "Academic"
        ADMINISTRATIVE = "ADMINISTRATIVE", "Administrative"
        SUPPORT = "SUPPORT", "Support"

    class EmploymentType(models.TextChoices):
        FULL_TIME = "FULL_TIME", "Full time"
        PART_TIME = "PART_TIME", "Part time"
        CONTRACT = "CONTRACT", "Contract"

    member = models.OneToOneField(
        CampusMember, on_delete=models.CASCADE, related_name="staff_profile"
    )
    position = models.CharField(max_length=80)
    staff_category = models.CharField(max_length=32, choices=Category.choices)
    employment_type = models.CharField(max_length=32, choices=EmploymentType.choices)
    hire_date = models.DateField(null=True, blank=True)
    office_code = models.CharField(max_length=32, blank=True)

    def __str__(self):
        return f"{self.position} ({self.member.campus_id})"

    def clean(self):
        if self.member_id and self.member.member_type != CampusMember.MemberType.STAFF:
            raise ValidationError("Staff details can only be saved on a staff member.")


class CheckIn(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Inside"
        CHECKED_OUT = "checked_out", "Checked out"

    member = models.ForeignKey(
        CampusMember, on_delete=models.CASCADE, related_name="check_ins"
    )
    checked_in_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )

    class Meta:
        ordering = ["-checked_in_at"]

    def __str__(self):
        return f"{self.member.campus_id} at {self.checked_in_at:%Y-%m-%d %H:%M}"
