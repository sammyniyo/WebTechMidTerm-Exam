import json
from functools import wraps

from django import forms
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from .forms import OfficeForm
from .models import Building, Office


def _error(message, status):
    return JsonResponse({"error": message}, status=status)


def _api_methods(*methods):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if request.method not in methods:
                response = _error("Method not allowed.", 405)
                response["Allow"] = ", ".join(methods)
                return response
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


def _form_errors(form):
    return JsonResponse(
        {"errors": form.errors.get_json_data()},
        status=400,
    )


def _read_json(request):
    if request.content_type != "application/json":
        return None, _error("Content-Type must be application/json.", 415)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, _error("Request body must contain valid JSON.", 400)

    if not isinstance(data, dict):
        return None, _error("JSON body must be an object.", 400)

    return data, None


def _staff_api_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return _error("Authentication is required.", 401)
        if not user.is_active or not user.is_staff:
            return _error("Staff access is required.", 403)
        return view_func(request, *args, **kwargs)

    return wrapped


def _building_data(building):
    return {
        "id": building.pk,
        "name": building.name,
        "description": building.description,
        "is_active": building.is_active,
    }


def _office_data(office):
    return {
        "id": office.pk,
        "name": office.name,
        "building": {
            "id": office.building_id,
            "name": office.building.name,
        },
        "floor": office.floor,
        "floor_display": office.get_floor_display(),
        "room_number": office.room_number,
        "directions": office.directions,
        "is_active": office.is_active,
    }


@_api_methods("GET", "POST")
def buildings(request):
    if request.method == "GET":
        rows = Building.objects.filter(is_active=True).values(
            "id", "name", "description", "is_active"
        )
        return JsonResponse({"results": list(rows)})

    return _create_building(request)


@_staff_api_required
def _create_building(request):
    data, error = _read_json(request)
    if error:
        return error

    data.setdefault("is_active", True)
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        return JsonResponse(
            {"errors": {"name": [{"message": "This field is required."}]}},
            status=400,
        )

    building = Building(name=name.strip())
    building_form = _BuildingForm(data, instance=building)
    if not building_form.is_valid():
        return _form_errors(building_form)

    try:
        building = building_form.save()
    except IntegrityError:
        return _error("A building with this name already exists.", 409)

    return JsonResponse(_building_data(building), status=201)


@_api_methods("GET", "PUT", "PATCH", "DELETE")
def building_detail(request, pk):
    if request.method == "GET":
        building = get_object_or_404(Building, pk=pk, is_active=True)
        return JsonResponse(_building_data(building))
    return _modify_building(request, pk)


@_staff_api_required
def _modify_building(request, pk):
    building = get_object_or_404(Building, pk=pk)

    if request.method == "DELETE":
        try:
            building.delete()
        except (IntegrityError, ValidationError):
            return _error(
                "This building cannot be deleted while offices are assigned to it.",
                409,
            )
        return JsonResponse({"deleted": True})

    data, error = _read_json(request)
    if error:
        return error
    if request.method == "PATCH":
        data = {
            **{
                "name": building.name,
                "description": building.description,
                "is_active": building.is_active,
            },
            **data,
        }

    form = _BuildingForm(data, instance=building)
    if not form.is_valid():
        return _form_errors(form)
    try:
        building = form.save()
    except IntegrityError:
        return _error("A building with this name already exists.", 409)
    return JsonResponse(_building_data(building))


@_api_methods("GET", "POST")
def offices(request):
    if request.method == "GET":
        rows = (
            Office.objects.filter(is_active=True, building__is_active=True)
            .select_related("building")
        )
        return JsonResponse({"results": [_office_data(row) for row in rows]})
    return _create_office(request)


@_staff_api_required
def _create_office(request):
    data, error = _read_json(request)
    if error:
        return error
    data.setdefault("is_active", True)
    form = OfficeForm(data)
    if not form.is_valid():
        return _form_errors(form)
    try:
        with transaction.atomic():
            office = form.save()
    except IntegrityError:
        return _error(
            "An office already exists in that building, floor, and room.",
            409,
        )
    return JsonResponse(_office_data(office), status=201)


@_api_methods("GET", "PUT", "PATCH", "DELETE")
def office_detail(request, pk):
    if request.method == "GET":
        office = get_object_or_404(
            Office.objects.select_related("building"),
            pk=pk,
            is_active=True,
            building__is_active=True,
        )
        return JsonResponse(_office_data(office))
    return _modify_office(request, pk)


@_staff_api_required
def _modify_office(request, pk):
    office = get_object_or_404(
        Office.objects.select_related("building"),
        pk=pk,
    )

    if request.method == "DELETE":
        office.delete()
        return JsonResponse({"deleted": True})

    data, error = _read_json(request)
    if error:
        return error
    if request.method == "PATCH":
        data = {
            **{
                "name": office.name,
                "building": office.building_id,
                "floor": office.floor,
                "room_number": office.room_number,
                "directions": office.directions,
                "is_active": office.is_active,
            },
            **data,
        }

    form = OfficeForm(data, instance=office)
    if not form.is_valid():
        return _form_errors(form)
    try:
        with transaction.atomic():
            office = form.save()
    except IntegrityError:
        return _error(
            "An office already exists in that building, floor, and room.",
            409,
        )
    return JsonResponse(_office_data(office))


class _BuildingForm(forms.ModelForm):
    class Meta:
        model = Building
        fields = ["name", "description", "is_active"]
