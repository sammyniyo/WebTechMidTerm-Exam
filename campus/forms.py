"""Campus forms. Branch owner: Jackson."""

from django import forms
from .models import Office


class OfficeForm(forms.ModelForm):
    class Meta:
        model = Office
        fields = [
            "name",
            "building",
            "floor",
            "room_number",
            "directions",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Registrar"}),
            "room_number": forms.TextInput(attrs={"placeholder": "200"}),
            "directions": forms.Textarea(attrs={"rows": 3, "placeholder": "How a visitor finds this office"}),
        }

