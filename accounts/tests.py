from types import SimpleNamespace

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, SimpleTestCase

from .decorators import gate_staff_required


class GateStaffRequiredTests(SimpleTestCase):
    def setUp(self):
        self.request = RequestFactory().get("/campus/offices/manage/")
        self.view = gate_staff_required(lambda request: request.path)

    def test_redirects_anonymous_users_to_staff_login(self):
        self.request.user = AnonymousUser()

        response = self.view(self.request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            "/login/?next=/campus/offices/manage/",
        )

    def test_denies_authenticated_non_staff_users(self):
        self.request.user = SimpleNamespace(
            is_authenticated=True,
            is_active=True,
            is_staff=False,
        )

        with self.assertRaises(PermissionDenied):
            self.view(self.request)

    def test_allows_active_staff_users(self):
        self.request.user = SimpleNamespace(
            is_authenticated=True,
            is_active=True,
            is_staff=True,
        )

        self.assertEqual(self.view(self.request), "/campus/offices/manage/")
