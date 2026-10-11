import re

from django import forms

from .models import VisitorVisit

NAME = re.compile(r"[A-Za-z][A-Za-z' .\-]{1,59}")


class VisitorRegistrationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].error_messages["required"] = "Enter a first name."
        self.fields["last_name"].error_messages["required"] = "Enter a last name."
        self.fields["phone"].error_messages["required"] = (
            "Enter a Rwandan mobile number, such as 078 000 0000."
        )
        self.fields["organization"].error_messages["required"] = (
            "Enter the organization you are coming from."
        )
        self.fields["destination"].error_messages["required"] = (
            "Enter the department or office you need."
        )

    class Meta:
        model = VisitorVisit
        fields = [
            "first_name",
            "last_name",
            "phone",
            "email",
            "organization",
            "destination",
            "host_name",
            "purpose",
        ]
        labels = {
            "first_name": "First name",
            "last_name": "Last name",
            "phone": "Phone",
            "email": "Email",
            "organization": "Organization",
            "destination": "Department or office",
            "host_name": "Person you are visiting",
            "purpose": "Reason",
        }
        widgets = {
            "first_name": forms.TextInput(attrs={"placeholder": "Aline", "autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"placeholder": "Uwase", "autocomplete": "family-name"}),
            "phone": forms.TextInput(attrs={"placeholder": "078 000 0000", "inputmode": "tel", "autocomplete": "tel"}),
            "email": forms.EmailInput(attrs={"placeholder": "name@example.com", "autocomplete": "email"}),
            "organization": forms.TextInput(attrs={"placeholder": "Company or institution"}),
            "destination": forms.TextInput(attrs={"placeholder": "Registrar, library, faculty office"}),
            "host_name": forms.TextInput(attrs={"placeholder": "Optional"}),
            "purpose": forms.Textarea(attrs={"placeholder": "A meeting, a document, registration", "rows": 3}),
        }

    def clean_first_name(self):
        return _clean_name(self.cleaned_data["first_name"], "Enter a first name using letters.")

    def clean_last_name(self):
        return _clean_name(self.cleaned_data["last_name"], "Enter a last name using letters.")

    def clean_phone(self):
        raw = re.sub(r"[\s\-()]", "", self.cleaned_data["phone"])
        if re.fullmatch(r"0?7\d{8}", raw):
            return "+250" + raw[-9:]
        if re.fullmatch(r"\+?2507\d{8}", raw):
            return "+250" + raw[-9:]
        raise forms.ValidationError("Enter a Rwandan mobile number, such as 078 000 0000.")

    def clean_organization(self):
        value = self.cleaned_data["organization"].strip()
        if len(value) < 2:
            raise forms.ValidationError("Enter the organization you are coming from.")
        return value

    def clean_destination(self):
        value = self.cleaned_data["destination"].strip()
        if len(value) < 2:
            raise forms.ValidationError("Enter the department or office you need.")
        return value

    def clean_host_name(self):
        value = self.cleaned_data.get("host_name", "").strip()
        if value and not NAME.fullmatch(value):
            raise forms.ValidationError("Use letters for the person's name, or leave it blank.")
        return value

    def clean_purpose(self):
        value = self.cleaned_data.get("purpose", "").strip()
        if value and len(value) < 3:
            raise forms.ValidationError("Add a short reason, or leave this blank.")
        return value

    def clean_email(self):
        return (self.cleaned_data.get("email") or "").strip()


def _clean_name(value, message):
    value = value.strip()
    if not NAME.fullmatch(value):
        raise forms.ValidationError(message)
    return value
