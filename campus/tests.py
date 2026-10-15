import json
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from .models import Building, Office


class CampusViewsTests(TestCase):
    def setUp(self):
        self.building = Building.objects.create(
            name="North Building",
            description="Test building",
        )
        self.office = Office.objects.create(
            name="Admissions",
            building=self.building,
            floor="1F",
            room_number="101",
            directions="Enter the north doors and turn left.",
        )
        user_model = get_user_model()
        self.staff = user_model.objects.create_user(
            username="campus-staff",
            password="test-password",
            is_staff=True,
        )

    def test_public_directory_shows_only_active_offices(self):
        inactive_office = Office.objects.create(
            name="Inactive Office",
            building=self.building,
            floor="2F",
            room_number="201",
            directions="Not open to visitors.",
            is_active=False,
        )
        inactive_building = Building.objects.create(
            name="Inactive Building",
            is_active=False,
        )
        hidden_office = Office.objects.create(
            name="Hidden Building Office",
            building=inactive_building,
            floor="1F",
            room_number="102",
            directions="Not open to visitors.",
        )

        response = self.client.get(reverse("campus:office_directory"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.office.name)
        self.assertNotContains(response, inactive_office.name)
        self.assertNotContains(response, hidden_office.name)

    def test_office_detail_shows_directions_and_hides_inactive_offices(self):
        response = self.client.get(
            reverse("campus:office_detail", args=[self.office.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.office.directions)
        self.office.is_active = False
        self.office.save()
        response = self.client.get(
            reverse("campus:office_detail", args=[self.office.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_staff_views_redirect_anonymous_users_and_deny_non_staff(self):
        path = reverse("campus:office_list")
        response = self.client.get(path)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={path}")

        non_staff = get_user_model().objects.create_user(
            username="campus-user",
            password="test-password",
        )
        denied_client = Client(raise_request_exception=False)
        denied_client.force_login(non_staff)
        response = denied_client.get(path)
        self.assertEqual(response.status_code, 403)

    def test_staff_can_create_update_and_confirm_delete_offices(self):
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("campus:office_create"),
            {
                "name": "Registrar",
                "building": self.building.pk,
                "floor": "2F",
                "room_number": "202",
                "directions": "Use the stairs to the second floor.",
                "is_active": "on",
            },
        )
        self.assertRedirects(response, reverse("campus:office_list"))
        created_office = Office.objects.get(name="Registrar")

        response = self.client.post(
            reverse("campus:office_update", args=[created_office.pk]),
            {
                "name": "Registrar Office",
                "building": self.building.pk,
                "floor": "2F",
                "room_number": "202",
                "directions": "Use the stairs to the second floor.",
                "is_active": "on",
            },
        )
        self.assertRedirects(response, reverse("campus:office_list"))
        created_office.refresh_from_db()
        self.assertEqual(created_office.name, "Registrar Office")

        delete_url = reverse("campus:office_delete", args=[created_office.pk])
        response = self.client.get(delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Office.objects.filter(pk=created_office.pk).exists())
        response = self.client.post(delete_url)
        self.assertRedirects(response, reverse("campus:office_list"))
        self.assertFalse(Office.objects.filter(pk=created_office.pk).exists())

    def test_office_form_rejects_missing_required_fields(self):
        self.client.force_login(self.staff)

        response = self.client.post(reverse("campus:office_create"), {})

        self.assertEqual(response.status_code, 200)
        form_errors = response.context["form"].errors
        self.assertEqual(form_errors["name"], ["This field is required."])
        self.assertEqual(form_errors["building"], ["This field is required."])
        self.assertEqual(form_errors["floor"], ["This field is required."])


class SampleCampusDataCommandTests(TestCase):
    def test_loading_sample_data_is_safe_to_repeat(self):
        output = StringIO()

        call_command("load_sample_campus", stdout=output)
        call_command("load_sample_campus", stdout=output)

        self.assertEqual(
            Building.objects.filter(name__startswith="Sample ").count(),
            3,
        )
        self.assertEqual(
            Office.objects.filter(name__startswith="Sample ").count(),
            4,
        )
        self.assertIn("SAMPLE DATA", output.getvalue())


class CampusApiTests(TestCase):
    def setUp(self):
        self.building = Building.objects.create(name="API Building")
        self.office = Office.objects.create(
            name="API Admissions",
            building=self.building,
            floor="1F",
            room_number="101",
            directions="Turn left at reception.",
        )
        self.staff = get_user_model().objects.create_user(
            username="api-staff",
            password="test-password",
            is_staff=True,
        )

    def _json_request(self, method, url, data=None):
        return getattr(self.client, method)(
            url,
            data=json.dumps(data) if data is not None else "",
            content_type="application/json",
        )

    def test_public_api_lists_active_buildings_and_offices_as_json(self):
        self.office.is_active = False
        self.office.save()

        buildings = self.client.get(reverse("campus:api_buildings"))
        offices = self.client.get(reverse("campus:api_offices"))

        self.assertEqual(buildings.status_code, 200)
        self.assertEqual(buildings["Content-Type"], "application/json")
        self.assertEqual(buildings.json()["results"][0]["name"], "API Building")
        self.assertEqual(offices.status_code, 200)
        self.assertEqual(offices.json()["results"], [])

    def test_writes_require_active_staff(self):
        url = reverse("campus:api_buildings")
        response = self._json_request(
            "post",
            url,
            {"name": "Created via API"},
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"], "Authentication is required.")

        non_staff = get_user_model().objects.create_user(
            username="api-user",
            password="test-password",
        )
        self.client.force_login(non_staff)
        response = self._json_request(
            "post",
            url,
            {"name": "Created via API"},
        )
        self.assertEqual(response.status_code, 403)

    def test_staff_can_create_update_and_delete_buildings(self):
        self.client.force_login(self.staff)
        url = reverse("campus:api_buildings")

        response = self._json_request(
            "post",
            url,
            {"name": "New API Building", "description": "Created with API"},
        )
        self.assertEqual(response.status_code, 201)
        building_id = response.json()["id"]
        detail_url = reverse("campus:api_building_detail", args=[building_id])

        response = self._json_request(
            "patch",
            detail_url,
            {"description": "Updated with API"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["description"], "Updated with API")

        response = self._json_request("delete", detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["deleted"])
        self.assertFalse(Building.objects.filter(pk=building_id).exists())

    def test_staff_can_create_update_and_delete_offices(self):
        self.client.force_login(self.staff)
        url = reverse("campus:api_offices")

        response = self._json_request(
            "post",
            url,
            {
                "name": "New API Office",
                "building": self.building.pk,
                "floor": "2F",
                "room_number": "202",
                "directions": "Go upstairs.",
            },
        )
        self.assertEqual(response.status_code, 201)
        office_id = response.json()["id"]
        detail_url = reverse("campus:api_office_detail", args=[office_id])

        response = self._json_request(
            "patch",
            detail_url,
            {"directions": "Take the stairs upstairs."},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["directions"], "Take the stairs upstairs.")

        response = self._json_request("delete", detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Office.objects.filter(pk=office_id).exists())

    def test_api_returns_json_errors_for_invalid_requests(self):
        self.client.force_login(self.staff)

        response = self._json_request(
            "post",
            reverse("campus:api_offices"),
            {"name": ""},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("errors", response.json())

        response = self.client.post(
            reverse("campus:api_buildings"),
            data="{invalid",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

        response = self.client.put(
            reverse("campus:api_buildings"),
            data="{}",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response["Allow"], "GET, POST")
