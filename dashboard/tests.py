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
		self.assertEqual(response.context["visitors_today"], 1)
		self.assertEqual(response.context["pending_visits"], 1)
		self.assertEqual(response.context["entries_today"], 1)
		self.assertEqual(response.context["active_offices"], 0)

	def test_searchable_visitor_list_and_gate_log(self):
		response = self.client.get(reverse("dashboard:visit_list"), {"q": "Aline"})
		self.assertContains(response, self.visit.reference_number)
		response = self.client.get(reverse("dashboard:gate_log"), {"q": self.visit.reference_number})
		self.assertEqual(response.status_code, 200)
