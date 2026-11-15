from django.test import TestCase
from django.urls import reverse

from gatepass.models import VisitorVisit


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

        from django.contrib.auth import get_user_model

        officer = get_user_model().objects.create_superuser("desk", "desk@example.com", "pass-word-123")
        self.client.force_login(officer)
        self.assertRedirects(self.client.get(scan), reverse("dashboard:visit_detail", args=[self.visit.reference_number]))

    def test_unknown_reference_has_no_qr(self):
        self.assertEqual(self.client.get(reverse("gatepass:visitor_qr", args=["AUC-NONE"])).status_code, 404)

    def test_gate_poster_is_for_staff_and_its_qr_is_public(self):
        self.assertEqual(self.client.get(reverse("gatepass:gate_qr")).status_code, 200)
        self.assertEqual(self.client.get(reverse("gatepass:gate_poster")).status_code, 302)
