from django import forms

from .models import CampusMember, StaffProfile, StudentProfile


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


class MemberRecordForm(forms.ModelForm):
    academic_level = forms.ChoiceField(
        choices=[("", "Choose a level"), *StudentProfile.AcademicLevel.choices],
        required=False,
        label="Academic level",
    )
    study_mode = forms.ChoiceField(
        choices=[("", "Choose a mode"), *StudentProfile.StudyMode.choices],
        required=False,
        label="Study mode",
    )
    position = forms.CharField(
        required=False,
        max_length=80,
        label="Position",
        widget=forms.TextInput(attrs={"placeholder": "Lecturer"}),
    )
    staff_category = forms.ChoiceField(
        choices=[("", "Choose a category"), *StaffProfile.Category.choices],
        required=False,
        label="Staff category",
    )
    employment_type = forms.ChoiceField(
        choices=[("", "Choose a type"), *StaffProfile.EmploymentType.choices],
        required=False,
        label="Employment",
    )
    office_code = forms.CharField(
        required=False,
        max_length=32,
        label="Office code",
        widget=forms.TextInput(attrs={"placeholder": "BUS-210"}),
    )

    class Meta:
        model = CampusMember
        fields = [
            "campus_id",
            "full_name",
            "member_type",
            "status",
            "department_code",
            "phone",
            "email",
        ]
        labels = {
            "campus_id": "Campus ID",
            "full_name": "Full name",
            "member_type": "Person",
            "status": "Status",
            "department_code": "Department",
            "phone": "Phone",
            "email": "Email",
        }
        widgets = {
            "campus_id": forms.TextInput(attrs={"placeholder": "20251MBI049"}),
            "full_name": forms.TextInput(attrs={"placeholder": "NIYOMUHOZA Samuel"}),
            "department_code": forms.TextInput(attrs={"placeholder": "MBI"}),
            "phone": forms.TextInput(attrs={"placeholder": "078 000 0000"}),
            "email": forms.EmailInput(attrs={"placeholder": "name@auca.ac.rw"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["member_type"].choices = CampusMember.MemberType.choices
        member = self.instance
        if not member.pk:
            if not self.is_bound:
                self.fields["member_type"].initial = CampusMember.MemberType.STUDENT
            return
        if member.member_type == CampusMember.MemberType.STUDENT:
            profile = StudentProfile.objects.filter(member=member).first()
            if profile:
                self.fields["academic_level"].initial = profile.academic_level
                self.fields["study_mode"].initial = profile.study_mode
        elif member.member_type == CampusMember.MemberType.STAFF:
            profile = StaffProfile.objects.filter(member=member).first()
            if profile:
                self.fields["position"].initial = profile.position
                self.fields["staff_category"].initial = profile.staff_category
                self.fields["employment_type"].initial = profile.employment_type
                self.fields["office_code"].initial = profile.office_code

    def clean_campus_id(self):
        return self.cleaned_data["campus_id"].strip()

    def clean_full_name(self):
        value = self.cleaned_data["full_name"].strip()
        if len(value) < 3:
            raise forms.ValidationError("Enter the full name.")
        return value

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get("member_type")
        if kind == CampusMember.MemberType.STUDENT:
            if not cleaned.get("academic_level"):
                self.add_error("academic_level", "Choose an academic level.")
            if not cleaned.get("study_mode"):
                self.add_error("study_mode", "Choose a study mode.")
        elif kind == CampusMember.MemberType.STAFF:
            if len((cleaned.get("position") or "").strip()) < 2:
                self.add_error("position", "Enter a position.")
            if not cleaned.get("staff_category"):
                self.add_error("staff_category", "Choose a staff category.")
            if not cleaned.get("employment_type"):
                self.add_error("employment_type", "Choose an employment type.")
        return cleaned

    def save(self, commit=True):
        member = super().save(commit=commit)
        if not commit:
            return member
        if member.member_type == CampusMember.MemberType.STUDENT:
            StaffProfile.objects.filter(member=member).delete()
            StudentProfile.objects.update_or_create(
                member=member,
                defaults={
                    "academic_level": self.cleaned_data["academic_level"],
                    "study_mode": self.cleaned_data["study_mode"],
                },
            )
        else:
            StudentProfile.objects.filter(member=member).delete()
            StaffProfile.objects.update_or_create(
                member=member,
                defaults={
                    "position": self.cleaned_data["position"].strip(),
                    "staff_category": self.cleaned_data["staff_category"],
                    "employment_type": self.cleaned_data["employment_type"],
                    "office_code": (self.cleaned_data.get("office_code") or "").strip(),
                },
            )
        return member
