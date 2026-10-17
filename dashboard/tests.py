from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class DashboardLayoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("desk", "desk@example.com", "pass-word")
        self.client.force_login(self.user)

    def test_overview_shows_the_four_figures(self):
        response = self.client.get(reverse("dashboard:home"))
        self.assertContains(response, "Visitors today")
        self.assertContains(response, "Pending")
        self.assertContains(response, "Entries today")
        self.assertContains(response, "Active offices")
        self.assertContains(response, "UWASE Keza")
        self.assertContains(response, "gate-side")
        self.assertNotContains(response, "adminlte")

    def test_ordinary_account_cannot_open_the_desk(self):
        person = User.objects.create_user("visitor-account", password="pass-word")
        self.client.force_login(person)
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 403)
        self.assertNotContains(response, "UWASE Keza", status_code=403)

    def test_visitor_list_detail_and_log(self):
        listing = self.client.get(reverse("dashboard:visitor_list"))
        self.assertContains(listing, "Search visitors")
        self.assertContains(listing, "AUC-4F2A91")

        detail = self.client.get(reverse("dashboard:visit_detail", args=["AUC-4F2A91"]))
        self.assertContains(detail, "Collect a transcript")
        self.assertContains(detail, "Registrar")

        missing = self.client.get(reverse("dashboard:visit_detail", args=["AUC-NONE"]))
        self.assertContains(missing, "No visit with this reference", status_code=404)

        log = self.client.get(reverse("dashboard:gate_log"))
        self.assertContains(log, "Gate log")
        self.assertContains(log, "NIYOMUHOZA Samuel")

    def test_anonymous_user_is_sent_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)
