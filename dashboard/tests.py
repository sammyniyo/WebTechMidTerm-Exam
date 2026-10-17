from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

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

    def test_anonymous_user_is_sent_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)
