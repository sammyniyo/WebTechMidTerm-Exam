import secrets
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from accounts.models import CampusMember


class VisitorVisit(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CHECKED_IN = "checked_in", "Checked in"
        COMPLETED = "completed", "Completed"

    reference_number = models.CharField(max_length=16, unique=True, editable=False)
    first_name = models.CharField(max_length=60)
    last_name = models.CharField(max_length=60)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    organization = models.CharField(max_length=120)
    destination = models.CharField(max_length=120)
    host_name = models.CharField(max_length=120, blank=True)
    purpose = models.TextField(blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateTimeField()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reference_number} · {self.full_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def save(self, *args, **kwargs):
        if not self.reference_number:
            self.reference_number = self._new_reference()
        if not self.valid_until:
            self.valid_until = timezone.now() + timedelta(hours=8)
        super().save(*args, **kwargs)

    @classmethod
    def _new_reference(cls):
        while True:
            number = "AUC-" + secrets.token_hex(6).upper()
            if not cls.objects.filter(reference_number=number).exists():
                return number


class GateEvent(models.Model):
    class EventType(models.TextChoices):
        ENTRY = "entry", "Entry"
        EXIT = "exit", "Exit"

    class Outcome(models.TextChoices):
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    visit = models.ForeignKey(
        VisitorVisit,
        on_delete=models.CASCADE,
        related_name="gate_events",
        null=True,
        blank=True,
    )
    member = models.ForeignKey(
        CampusMember,
        on_delete=models.PROTECT,
        related_name="gate_events",
        null=True,
        blank=True,
    )
    event_type = models.CharField(max_length=8, choices=EventType.choices)
    occurred_at = models.DateTimeField(default=timezone.now)
    officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="gate_events",
    )
    outcome = models.CharField(max_length=8, choices=Outcome.choices)

    class Meta:
        ordering = ["-occurred_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(visit__isnull=False, member__isnull=True)
                    | Q(visit__isnull=True, member__isnull=False)
                ),
                name="gate_event_exactly_one_person",
            )
        ]

    def __str__(self):
        person = self.visit or self.member
        return f"{self.get_event_type_display()} · {person} · {self.occurred_at:%Y-%m-%d %H:%M}"

    def clean(self):
        super().clean()
        if (self.visit_id is None) == (self.member_id is None):
            raise ValidationError("A gate event must belong to exactly one visit or campus member.")
