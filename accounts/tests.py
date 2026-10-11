from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from accounts.models import CampusMember, StaffProfile, StudentProfile
from accounts.roles import SECURITY_OFFICER
from accounts.services import verify_campus_id


class VerifyCampusIdTests(TestCase):
    def setUp(self):
        student = CampusMember.objects.create(
            campus_id="20251MBI049",
            internal_id=101655,
            member_type=CampusMember.MemberType.STUDENT,
            full_name="NIYOMUHOZA Samuel",
            status=CampusMember.Status.ACTIVE,
            department_code="MBI",
        )
        StudentProfile.objects.create(
            member=student,
            academic_level=StudentProfile.AcademicLevel.GRADUATE,
            study_mode=StudentProfile.StudyMode.MASTERS,
            admitted_term_id="2025/1",
        )
        staff = CampusMember.objects.create(
            campus_id="STF2016BUS008",
            internal_id=50016,
            member_type=CampusMember.MemberType.STAFF,
            full_name="MUKAMANA Grace",
            status=CampusMember.Status.ACTIVE,
            department_code="BUS",
        )
        StaffProfile.objects.create(
            member=staff,
            position="Lecturer",
            staff_category=StaffProfile.Category.ACADEMIC,
            employment_type=StaffProfile.EmploymentType.FULL_TIME,
            office_code="BUS-210",
        )
        CampusMember.objects.create(
            campus_id="STF2022SEC001",
            member_type=CampusMember.MemberType.STAFF,
            full_name="INGABIRE Aline",
            status=CampusMember.Status.ON_LEAVE,
            department_code="SEC",
        )

    def test_active_student_is_allowed(self):
        result = verify_campus_id("20251mbi049", "student")
        self.assertTrue(result["verified"])
        self.assertEqual(result["access"], "allowed")
        self.assertEqual(result["member"]["recordId"], CampusMember.objects.get(campus_id="20251MBI049").pk)
        self.assertNotIn("idNumber", result["member"])

    def test_unknown_id_is_denied(self):
        result = verify_campus_id("NO-SUCH-ID", "student")
        self.assertFalse(result["verified"])
        self.assertIsNone(result["member"])

    def test_staff_on_leave_is_identified_but_not_admitted(self):
        result = verify_campus_id("STF2022SEC001", "staff")
        self.assertTrue(result["verified"])
        self.assertEqual(result["access"], "denied")
        self.assertIn("On leave", result["reason"])

    def test_wrong_type_does_not_grant_access(self):
        result = verify_campus_id("STF2016BUS008", "student")
        self.assertTrue(result["verified"])
        self.assertEqual(result["access"], "denied")

    def test_verify_page_renders_result(self):
        response = self.client.post(
            reverse("accounts:verify"),
            {"member_type": "student", "campus_id": "20251MBI049"},
        )
        self.assertContains(response, "NIYOMUHOZA Samuel")
        self.assertContains(response, "allowed")

    def test_verify_api_matches_the_service(self):
        response = self.client.get(
            reverse("accounts:verify_api"),
            {"id": "20251MBI049", "member_type": "student"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["access"], "allowed")
        self.assertEqual(body["member"]["memberType"], "student")

    def test_full_student_record_uses_the_source_shape(self):
        officer = User.objects.create_user("officer", password="gate-pass-test")
        group, _ = Group.objects.get_or_create(name=SECURITY_OFFICER)
        officer.groups.add(group)
        self.client.force_login(officer)

        response = self.client.get(
            reverse("accounts:member_detail_api", args=["20251MBI049"])
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["id"], "20251MBI049")
        self.assertEqual(body["academicLevel"], "GRADUATE")
        self.assertEqual(body["studyMode"], "MASTERS")
        self.assertNotIn("position", body)

    def test_full_staff_record_uses_the_staff_shape(self):
        officer = User.objects.create_user("desk", password="gate-pass-test")
        officer.groups.add(Group.objects.get_or_create(name=SECURITY_OFFICER)[0])
        self.client.force_login(officer)

        response = self.client.get(
            reverse("accounts:member_detail_api", args=["STF2016BUS008"])
        )
        body = response.json()
        self.assertEqual(body["position"], "Lecturer")
        self.assertEqual(body["staffCategory"], "ACADEMIC")
        self.assertEqual(body["employmentType"], "FULL_TIME")
        self.assertEqual(body["officeCode"], "BUS-210")
        self.assertNotIn("academicLevel", body)

    def test_full_record_is_closed_to_anonymous_callers(self):
        response = self.client.get(
            reverse("accounts:member_detail_api", args=["20251MBI049"])
        )
        self.assertEqual(response.status_code, 401)
