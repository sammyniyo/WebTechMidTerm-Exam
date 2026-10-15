
from django.db import models


class Building(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Office(models.Model):
    FLOOR_CHOICES = [
        ("BL", "Basement Level"),
        ("1F", "First Floor"),
        ("2F", "Second Floor"),
        ("3F", "Third Floor"),
    ]

    name = models.CharField(max_length=150)
    building = models.ForeignKey(
        Building,
        on_delete=models.PROTECT,
        related_name="offices",
    )
    floor = models.CharField(max_length=2, choices=FLOOR_CHOICES)
    room_number = models.CharField(max_length=20)
    directions = models.TextField(
        help_text="Explain how a visitor can find this office."
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["building__name", "floor", "room_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["building", "floor", "room_number"],
                name="unique_office_room_per_building_floor",
            )
        ]

    def __str__(self):
        return f"{self.name} - Room {self.room_number}"
