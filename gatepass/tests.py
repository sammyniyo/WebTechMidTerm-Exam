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
