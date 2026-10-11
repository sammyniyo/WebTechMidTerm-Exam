from .models import CampusMember


def _blank(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def member_summary(member):
    """Fields other apps may show at the gate. No national ID or birth date."""
    return {
        "recordId": member.pk,
        "id": member.campus_id,
        "internalId": member.internal_id,
        "memberType": member.member_type,
        "name": member.full_name,
        "status": member.status,
        "departmentCode": member.department_code or None,
        "email": member.email or None,
        "phoneNo": member.phone or None,
    }


def member_source(member):
    """Full campus record. Student and staff shapes share the identity fields."""
    payload = {
        "recordId": member.pk,
        "id": member.campus_id,
        "internalId": member.internal_id,
        "memberType": member.member_type,
        "name": member.full_name,
        "sex": member.sex or None,
        "maritalStatus": member.marital_status or None,
        "birthDate": member.birth_date,
        "nationality": member.nationality or None,
        "idNumber": member.national_id,
        "actualAddress": member.actual_address or None,
        "religion": member.religion or None,
        "status": member.status,
        "phoneNo": member.phone or None,
        "email": member.email or None,
        "departmentCode": member.department_code or None,
        "accountCode": member.account_code or None,
        "disabilityStatus": member.disability_status,
        "disabilityDetails": member.disability_details or None,
        "profileComplete": member.profile_complete,
        "missingProfileFields": member.missing_profile_fields or [],
        "hasProfilePicture": member.has_profile_picture,
        "profilePictureUpdatedAt": member.profile_picture_updated_at,
    }
    student = getattr(member, "student_profile", None)
    if student is not None:
        payload.update(
            {
                "academicLevel": student.academic_level,
                "studyMode": student.study_mode,
                "admittedTermId": student.admitted_term_id or None,
                "highSchoolName": student.high_school_name or None,
                "highSchoolCombination": student.high_school_combination or None,
                "highSchoolLocation": student.high_school_location or None,
                "highSchoolId": student.high_school_id,
                "secondarySchoolAggregateScore": student.secondary_school_aggregate_score,
            }
        )
    staff = getattr(member, "staff_profile", None)
    if staff is not None:
        payload.update(
            {
                "position": staff.position,
                "staffCategory": staff.staff_category,
                "employmentType": staff.employment_type,
                "hireDate": staff.hire_date,
                "officeCode": staff.office_code or None,
            }
        )
    return payload


def verify_campus_id(campus_id, member_type=None):
    """Check a campus card ID.

    Identity and access are separate. A matching record can still be denied
    when the person is inactive, suspended, on leave, or the wrong type.
    """
    campus_id = _blank(campus_id)
    member_type = _blank(member_type)
    if member_type:
        member_type = member_type.lower()

    if not campus_id:
        return {
            "ok": False,
            "verified": False,
            "access": "denied",
            "reason": "Enter a campus ID.",
            "member": None,
        }

    if member_type and member_type not in CampusMember.MemberType.values:
        return {
            "ok": False,
            "verified": False,
            "access": "denied",
            "reason": "member_type must be student or staff.",
            "member": None,
        }

    member = (
        CampusMember.objects.filter(campus_id__iexact=campus_id)
        .select_related("student_profile", "staff_profile")
        .first()
    )
    if member is None:
        return {
            "ok": True,
            "verified": False,
            "access": "denied",
            "reason": "No campus record matches this ID.",
            "member": None,
        }

    summary = member_summary(member)
    if member_type and member.member_type != member_type:
        label = member.get_member_type_display().lower()
        return {
            "ok": True,
            "verified": True,
            "access": "denied",
            "reason": f"This ID belongs to a {label} record.",
            "member": summary,
        }

    if not member.is_active_member:
        return {
            "ok": True,
            "verified": True,
            "access": "denied",
            "reason": f"Record status is {member.get_status_display()}.",
            "member": summary,
        }

    label = member.get_member_type_display().lower()
    return {
        "ok": True,
        "verified": True,
        "access": "allowed",
        "reason": f"Active {label} record.",
        "member": summary,
    }
