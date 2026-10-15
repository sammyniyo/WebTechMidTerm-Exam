from django import forms

from .models import CampusMember


class VerifyMemberForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.fields["member_type"].initial = CampusMember.MemberType.STUDENT

    member_type = forms.ChoiceField(
        choices=CampusMember.MemberType.choices,
        widget=forms.RadioSelect,
    )
    campus_id = forms.CharField(
        max_length=32,
        label="Campus ID",
        widget=forms.TextInput(
            attrs={
                "placeholder": "20251MBI049",
                "autocomplete": "off",
                "autocapitalize": "characters",
                "spellcheck": "false",
            }
        ),
    )

    def clean_campus_id(self):
        return self.cleaned_data["campus_id"].strip()
