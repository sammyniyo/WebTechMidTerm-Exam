import secrets
from datetime import timedelta

from django.db import models
from django.utils import timezone


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
            number = "AUC-" + secrets.token_hex(3).upper()
            if not cls.objects.filter(reference_number=number).exists():
                return number
