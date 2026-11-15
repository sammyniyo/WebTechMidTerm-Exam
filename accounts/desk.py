from django.contrib import messages
from django.db.models import ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from accounts.decorators import gate_staff_required
from accounts.forms import MemberRecordForm
from accounts.models import CampusMember
from dashboard.paging import paginate


def _initials(name):
    parts = [part for part in (name or "").split() if part]
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return ((name or "?")[:2]).upper()


@gate_staff_required
def member_list(request):
    query = request.GET.get("q", "").strip()
    kind = request.GET.get("type", "").strip().lower()
    members = CampusMember.objects.all()
    if kind in CampusMember.MemberType.values:
        members = members.filter(member_type=kind)
    else:
        kind = ""
    if query:
        members = members.filter(
            Q(full_name__icontains=query)
            | Q(campus_id__icontains=query)
            | Q(department_code__icontains=query)
        )
    page = paginate(request, members)
    rows = [
        {
            "id": member.pk,
            "initials": _initials(member.full_name),
            "name": member.full_name,
            "campus_id": member.campus_id,
            "kind": member.get_member_type_display(),
            "department": member.department_code or "—",
            "status": member.status,
            "status_label": member.get_status_display(),
        }
        for member in page.object_list
    ]
    return render(
        request,
        "dashboard/people.html",
        {
            "section": "people",
            "people": rows,
            "page_obj": page,
            "query": query,
            "kind": kind,
        },
    )


@gate_staff_required
def member_create(request):
    form = MemberRecordForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        member = form.save()
        messages.success(request, f"{member.full_name} was added.")
        return redirect("dashboard:member_list")
    return render(
        request,
        "dashboard/person_form.html",
        {"form": form, "page_title": "New person", "section": "people"},
    )


@gate_staff_required
def member_update(request, pk):
    member = get_object_or_404(CampusMember, pk=pk)
    form = MemberRecordForm(
        request.POST if request.method == "POST" else None,
        instance=member,
    )
    if request.method == "POST" and form.is_valid():
        member = form.save()
        messages.success(request, f"{member.full_name} was updated.")
        return redirect("dashboard:member_list")
    return render(
        request,
        "dashboard/person_form.html",
        {
            "form": form,
            "page_title": member.full_name,
            "section": "people",
            "member": member,
        },
    )


@gate_staff_required
@require_http_methods(["GET", "POST"])
def member_delete(request, pk):
    member = get_object_or_404(CampusMember, pk=pk)
    if request.method == "POST":
        name = member.full_name
        try:
            member.delete()
        except ProtectedError:
            member.status = CampusMember.Status.INACTIVE
            member.save(update_fields=["status"])
            messages.error(
                request,
                f"{name} has gate records, so the record was marked inactive.",
            )
        else:
            messages.success(request, f"{name} was removed.")
        return redirect("dashboard:member_list")
    return render(
        request,
        "dashboard/person_confirm_delete.html",
        {"member": member, "section": "people"},
    )
