
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from accounts.decorators import gate_staff_required
from .forms import OfficeForm
from .models import Building, Office


def office_directory(request):
    """Show active buildings and offices to the public."""
    offices = (
        Office.objects.filter(
            is_active=True,
            building__is_active=True,
        )
        .select_related("building")
    )

    return render(
        request,
        "campus/office_directory.html",
        {"offices": offices},
    )


def office_detail(request, pk):
    """Show the location and directions for one active office."""
    office = get_object_or_404(
        Office.objects.select_related("building"),
        pk=pk,
        is_active=True,
        building__is_active=True,
    )

    return render(
        request,
        "campus/office_detail.html",
        {"office": office},
    )


@gate_staff_required
def office_list(request):
    """List offices for staff management."""
    offices = Office.objects.select_related("building")
    return render(
        request,
        "campus/office_list.html",
        {"offices": offices},
    )


@gate_staff_required
def office_create(request):
    """Create a new office."""
    form = OfficeForm(
        request.POST if request.method == "POST" else None,
    )

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Office created successfully.")
        return redirect("campus:office_list")

    return render(
        request,
        "campus/office_form.html",
        {"form": form, "page_title": "Create Office"},
    )


@gate_staff_required
def office_update(request, pk):
    """Update an existing office."""
    office = get_object_or_404(Office, pk=pk)
    form = OfficeForm(
        request.POST if request.method == "POST" else None,
        instance=office,
    )

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Office updated successfully.")
        return redirect("campus:office_list")

    return render(
        request,
        "campus/office_form.html",
        {"form": form, "page_title": "Update Office"},
    )


@gate_staff_required
def office_delete(request, pk):
    """Delete an office only after confirmation."""
    office = get_object_or_404(Office, pk=pk)

    if request.method == "POST":
        office.delete()
        messages.success(request, "Office deleted successfully.")
        return redirect("campus:office_list")

    return render(
        request,
        "campus/office_confirm_delete.html",
        {"office": office},
    )


@gate_staff_required
def building_list(request):
    """List buildings for staff management."""
    buildings = Building.objects.all()
    return render(
        request,
        "campus/building_list.html",
        {"buildings": buildings},
    )
