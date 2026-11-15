from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import CampusMember
from gatepass.models import GateEvent, VisitorVisit


class VisitorRegistrationTests(TestCase):
    def test_guest_form_fetches_the_building_api(self):
        response = self.client.get(reverse("gatepass:visitor_register"))
        self.assertContains(response, reverse("campus:api_buildings"))
        self.assertContains(response, 'id="id_building"')

    def test_missing_details_are_rejected(self):
        response = self.client.post(reverse("gatepass:visitor_register"), {})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter a first name.")
        self.assertContains(response, "Enter a Rwandan mobile number")
        self.assertContains(response, "Enter the department or office you need.")
        self.assertEqual(VisitorVisit.objects.count(), 0)

    def test_short_phone_is_rejected(self):
        response = self.client.post(
            reverse("gatepass:visitor_register"),
            {
                "first_name": "Aline",
                "last_name": "Uwase",
                "phone": "078",
                "organization": "AUCA",
                "destination": "Registrar",
            },
        )
        self.assertContains(response, "Enter a Rwandan mobile number")
        self.assertEqual(VisitorVisit.objects.count(), 0)

    def test_complete_visit_is_pending_and_hides_the_form(self):
        response = self.client.post(
            reverse("gatepass:visitor_register"),
            {
                "first_name": "Aline",
                "last_name": "Uwase",
                "phone": "078 000 0000",
                "email": "aline@example.com",
                "organization": "City Library",
                "destination": "Registrar",
                "host_name": "Eric Habimana",
                "purpose": "Collect a document",
            },
        )
        visit = VisitorVisit.objects.get()
        self.assertEqual(visit.status, VisitorVisit.Status.PENDING)
        self.assertEqual(visit.phone, "+250780000000")
        self.assertTrue(visit.reference_number.startswith("AUC-"))
        self.assertContains(response, visit.reference_number)
        self.assertContains(response, "pending")
        self.assertNotContains(response, "Department or office")


class VisitorQRCodeTests(TestCase):
    def setUp(self):
        self.visit = VisitorVisit.objects.create(
            first_name="Aline", last_name="Uwase", phone="+250780000000",
            organization="City Library", destination="Registrar",
        )

    def test_pass_shows_a_qr_that_leads_to_the_scan_page(self):
        page = self.client.get(reverse("gatepass:visitor_pass", args=[self.visit.reference_number]))
        self.assertContains(page, reverse("gatepass:visitor_qr", args=[self.visit.reference_number]))

        image = self.client.get(reverse("gatepass:visitor_qr", args=[self.visit.reference_number]))
        self.assertEqual(image["Content-Type"], "image/svg+xml")
        self.assertTrue(image.content.lstrip().startswith(b"<?xml") or b"<svg" in image.content[:200])

        download = self.client.get(reverse("gatepass:visitor_qr", args=[self.visit.reference_number]), {"download": 1})
        self.assertIn("attachment", download["Content-Disposition"])

    def test_scan_sends_officers_to_the_desk_and_visitors_to_the_pass(self):
        scan = reverse("gatepass:visitor_scan", args=[self.visit.reference_number])
        self.assertRedirects(self.client.get(scan), reverse("gatepass:visitor_pass", args=[self.visit.reference_number]))

        officer = get_user_model().objects.create_superuser("desk", "desk@example.com", "pass-word-123")
        self.client.force_login(officer)
        self.assertRedirects(self.client.get(scan), reverse("dashboard:visit_detail", args=[self.visit.reference_number]))

    def test_unknown_reference_has_no_qr(self):
        self.assertEqual(self.client.get(reverse("gatepass:visitor_qr", args=["AUC-NONE"])).status_code, 404)

    def test_gate_poster_is_for_staff_and_its_qr_is_public(self):
        self.assertEqual(self.client.get(reverse("gatepass:gate_qr")).status_code, 200)
        self.assertEqual(self.client.get(reverse("gatepass:gate_poster")).status_code, 302)


# Gate workflow tests from JP's branch (PR #6).
class GateWorkflowTests(TestCase):
    def setUp(self):
        self.officer = get_user_model().objects.create_superuser(
            username="officer", email="officer@example.com", password="test-password"
        )
        self.visit = VisitorVisit.objects.create(
            first_name="Aline",
            last_name="Uwase",
            phone="+250780000000",
            organization="City Library",
            destination="Registrar",
            valid_until=timezone.now() + timedelta(hours=2),
        )
        self.client.force_login(self.officer)

    def test_public_pass_displays_visit_status(self):
        response = self.client.get(
            reverse("gatepass:visitor_pass", args=[self.visit.reference_number])
        )
        self.assertContains(response, self.visit.reference_number)
        self.assertContains(response, "Pending")

    def test_approval_entry_and_exit_update_visit_and_log_events(self):
        review_url = reverse("gatepass:review_visit", args=[self.visit.reference_number])
        gate_url = reverse("gatepass:record_gate_event", args=[self.visit.reference_number])

        response = self.client.post(review_url, {"decision": "approve"})
        self.assertRedirects(
            response,
            reverse("dashboard:visit_detail", args=[self.visit.reference_number]),
        )
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.status, VisitorVisit.Status.APPROVED)

        self.client.post(gate_url, {"event_type": GateEvent.EventType.ENTRY})
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.status, VisitorVisit.Status.CHECKED_IN)
        self.assertEqual(self.visit.gate_events.get().outcome, GateEvent.Outcome.ACCEPTED)

        self.client.post(gate_url, {"event_type": GateEvent.EventType.EXIT})
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.status, VisitorVisit.Status.COMPLETED)
        self.assertEqual(self.visit.gate_events.count(), 2)

    def test_pending_or_expired_visits_cannot_be_checked_in(self):
        gate_url = reverse("gatepass:record_gate_event", args=[self.visit.reference_number])
        self.client.post(gate_url, {"event_type": GateEvent.EventType.ENTRY})
        self.assertEqual(self.visit.gate_events.get().outcome, GateEvent.Outcome.REJECTED)

        self.visit.status = VisitorVisit.Status.APPROVED
        self.visit.valid_until = timezone.now() - timedelta(minutes=1)
        self.visit.save(update_fields=["status", "valid_until"])
        self.client.post(gate_url, {"event_type": GateEvent.EventType.ENTRY})
        self.assertEqual(self.visit.gate_events.count(), 2)
        self.assertEqual(
            self.visit.gate_events.order_by("occurred_at").last().outcome,
            GateEvent.Outcome.REJECTED,
        )

    def test_gate_event_requires_exactly_one_person(self):
        member = CampusMember.objects.create(
            campus_id="STU-001", member_type=CampusMember.MemberType.STUDENT, full_name="Sample Student"
        )
        event = GateEvent(
            visit=self.visit,
            member=member,
            event_type=GateEvent.EventType.ENTRY,
            officer=self.officer,
            outcome=GateEvent.Outcome.ACCEPTED,
        )
        with self.assertRaises(ValidationError):
            event.full_clean()

        event.visit = None
        event.member = None
        with self.assertRaises(ValidationError):
            event.full_clean()
