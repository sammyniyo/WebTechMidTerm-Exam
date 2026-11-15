from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import CampusMember, CheckIn, StudentProfile
from gatepass.models import GateEvent, VisitorVisit


class DashboardTests(TestCase):
    def setUp(self):
        self.officer = get_user_model().objects.create_superuser(
            username="admin", email="admin@example.com", password="test-password"
        )
        self.client.force_login(self.officer)
        self.visit = VisitorVisit.objects.create(
            first_name="Aline",
            last_name="Uwase",
            phone="+250780000000",
            organization="City Library",
            destination="Registrar",
            valid_until=timezone.now() + timedelta(hours=1),
        )

    def test_dashboard_counts_database_totals(self):
        GateEvent.objects.create(
            visit=self.visit,
            event_type=GateEvent.EventType.ENTRY,
            officer=self.officer,
            outcome=GateEvent.Outcome.ACCEPTED,
        )
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Visitors today")
        self.assertContains(response, "gate-side")
        self.assertNotContains(response, "adminlte")
        self.assertEqual(response.context["visitors_today"], 1)
        self.assertEqual(response.context["pending_visits"], 1)
        self.assertEqual(response.context["entries_today"], 1)
        self.assertEqual(response.context["active_offices"], 0)
        self.assertContains(response, "Aline Uwase")

    def test_searchable_visitor_list_and_gate_log(self):
        response = self.client.get(reverse("dashboard:visit_list"), {"q": "Aline"})
        self.assertContains(response, self.visit.reference_number)
        self.assertContains(response, "Search visitors")
        response = self.client.get(reverse("dashboard:gate_log"), {"q": self.visit.reference_number})
        self.assertEqual(response.status_code, 200)

    def test_ordinary_account_cannot_open_the_desk(self):
        person = get_user_model().objects.create_user("visitor-account", password="pass-word")
        self.client.force_login(person)
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 403)
        self.assertNotContains(response, "Aline Uwase", status_code=403)

    def test_missing_visit_explains_the_gap(self):
        response = self.client.get(reverse("dashboard:visit_detail", args=["AUC-NONE"]))
        self.assertContains(response, "No visit with this reference", status_code=404)

    def test_check_in_desk_approves_and_checks_out_with_timestamps(self):
        member = CampusMember.objects.create(
            campus_id="20251MBI049",
            member_type=CampusMember.MemberType.STUDENT,
            full_name="NIYOMUHOZA Samuel",
            status=CampusMember.Status.ACTIVE,
        )
        check_in = CheckIn.objects.create(member=member)
        page = self.client.get(reverse("dashboard:check_ins"))
        self.assertContains(page, "Approve")
        self.assertContains(page, "People")
        self.assertNotContains(page, "Django admin")
        self.assertContains(page, timezone.localtime(check_in.checked_in_at).strftime("%H:%M"))

        approved = self.client.post(reverse("dashboard:approve_check_in", args=[check_in.pk]))
        self.assertRedirects(approved, reverse("dashboard:check_ins"))
        check_in.refresh_from_db()
        self.assertEqual(check_in.status, CheckIn.Status.APPROVED)
        self.assertIsNotNone(check_in.approved_at)

        inside = self.client.get(reverse("dashboard:check_ins"))
        self.assertContains(inside, "Checkout")
        self.assertContains(inside, timezone.localtime(check_in.approved_at).strftime("%H:%M"))

        left = self.client.post(reverse("dashboard:checkout_check_in", args=[check_in.pk]))
        self.assertRedirects(left, reverse("dashboard:check_ins"))
        check_in.refresh_from_db()
        self.assertEqual(check_in.status, CheckIn.Status.CHECKED_OUT)
        self.assertIsNotNone(check_in.checked_out_at)

    def test_officer_can_add_a_student_and_a_staff_member(self):
        student = self.client.post(
            reverse("dashboard:member_create"),
            {
                "campus_id": "20261CSC001",
                "full_name": "Keza Aline",
                "member_type": "student",
                "status": "ACTIVE",
                "department_code": "CSC",
                "phone": "",
                "email": "",
                "academic_level": "UNDERGRADUATE",
                "study_mode": "DAY",
                "position": "",
                "staff_category": "",
                "employment_type": "",
                "office_code": "",
            },
        )
        self.assertRedirects(student, reverse("dashboard:member_list"))
        created = CampusMember.objects.get(campus_id="20261CSC001")
        self.assertEqual(created.student_profile.academic_level, StudentProfile.AcademicLevel.UNDERGRADUATE)

        missing = self.client.post(
            reverse("dashboard:member_create"),
            {
                "campus_id": "STF2099BUS001",
                "full_name": "Eric Habimana",
                "member_type": "staff",
                "status": "ACTIVE",
                "department_code": "BUS",
                "phone": "",
                "email": "",
                "academic_level": "",
                "study_mode": "",
                "position": "",
                "staff_category": "",
                "employment_type": "",
                "office_code": "",
            },
        )
        self.assertContains(missing, "Enter a position.")
        self.assertFalse(CampusMember.objects.filter(campus_id="STF2099BUS001").exists())

        staff = self.client.post(
            reverse("dashboard:member_create"),
            {
                "campus_id": "STF2099BUS001",
                "full_name": "Eric Habimana",
                "member_type": "staff",
                "status": "ACTIVE",
                "department_code": "BUS",
                "phone": "",
                "email": "",
                "academic_level": "",
                "study_mode": "",
                "position": "Lecturer",
                "staff_category": "ACADEMIC",
                "employment_type": "FULL_TIME",
                "office_code": "BUS-210",
            },
        )
        self.assertRedirects(staff, reverse("dashboard:member_list"))
        record = CampusMember.objects.get(campus_id="STF2099BUS001")
        self.assertEqual(record.staff_profile.position, "Lecturer")
        self.assertFalse(StudentProfile.objects.filter(member=record).exists())

        listed = self.client.get(reverse("dashboard:member_list"), {"q": "Keza"})
        self.assertContains(listed, "20261CSC001")
        self.assertContains(listed, "New person")

    def test_people_list_is_paginated(self):
        for index in range(9):
            CampusMember.objects.create(
                campus_id=f"PAG{index:03d}",
                member_type=CampusMember.MemberType.STUDENT,
                full_name=f"Page Person {index:02d}",
                status=CampusMember.Status.ACTIVE,
            )
        first = self.client.get(reverse("dashboard:member_list"))
        self.assertContains(first, "Page 1 of")
        self.assertContains(first, "Next")
        second = self.client.get(reverse("dashboard:member_list"), {"page": 2})
        self.assertContains(second, "Page 2 of")
        self.assertContains(second, "Page Person 08")
        self.assertContains(second, "Previous")

    def test_anonymous_user_is_sent_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)
