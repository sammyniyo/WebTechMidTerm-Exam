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
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. Faculty of IT",
            }),
            "building": forms.Select(attrs={
                "class": "form-control",
            }),
            "floor": forms.Select(attrs={
                "class": "form-control",
            }),
            "room_number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. 200",
            }),
            "directions": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Describe how to find the office",
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
        }

