import json

from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .forms import VerifyMemberForm
from .models import CampusMember
from .roles import user_can_manage_gate
from .services import member_source, member_summary, verify_campus_id


def verify_member(request):
    form = VerifyMemberForm(request.POST if request.method == "POST" else None)
    result = None
    if request.method == "POST" and form.is_valid():
        result = verify_campus_id(
            form.cleaned_data["campus_id"],
            form.cleaned_data["member_type"],
        )
    return render(
        request,
        "accounts/verify.html",
        {"form": form, "result": result},
    )


def _json(payload, status=200):
    return JsonResponse(payload, status=status, encoder=DjangoJSONEncoder)


def _read_body(request):
    if request.method == "GET":
        return request.GET
    if request.content_type and "json" in request.content_type:
        try:
            body = json.loads(request.body.decode() or "{}")
        except json.JSONDecodeError as exc:
            raise ValidationError("Send valid JSON.") from exc
        if not isinstance(body, dict):
            raise ValidationError("JSON body must be an object.")
        return body
    return request.POST


@csrf_exempt
@require_http_methods(["GET", "POST"])
def verify_api(request):
    """Public identity check used by the gate app and the verify page.

    GET  /api/accounts/verify/?id=20251MBI049&member_type=student
    POST /api/accounts/verify/   {"id": "20251MBI049", "member_type": "student"}

    ``member_type`` is optional. ``campus_id`` is accepted as an alias of ``id``.
    """
    try:
        payload = _read_body(request)
    except ValidationError as exc:
        return _json(
            {
                "ok": False,
                "verified": False,
                "access": "denied",
                "reason": exc.messages[0],
                "member": None,
            },
            status=400,
        )

    campus_id = payload.get("id") or payload.get("campus_id")
    result = verify_campus_id(campus_id, payload.get("member_type"))
    return _json(result, status=200 if result["ok"] else 400)


def _gate_staff_json(request):
    if not request.user.is_authenticated:
        return _json({"reason": "Sign in required."}, status=401)
    if not user_can_manage_gate(request.user):
        return _json(
            {"reason": "Security officer or administrator only."},
            status=403,
        )
    return None


@require_http_methods(["GET"])
def member_list_api(request):
    """Authorized list. Returns the short gate record, not national IDs.

    GET /api/accounts/members/?member_type=staff&status=ACTIVE&department_code=MBI&q=niyo
    """
    denied = _gate_staff_json(request)
    if denied:
        return denied

    members = CampusMember.objects.all().select_related(
        "student_profile", "staff_profile"
    )
    member_type = (request.GET.get("member_type") or "").strip().lower()
    status = (request.GET.get("status") or "").strip().upper()
    department = (request.GET.get("department_code") or "").strip()
    query = (request.GET.get("q") or "").strip()

    if member_type:
        if member_type not in CampusMember.MemberType.values:
            return _json({"reason": "member_type must be student or staff."}, status=400)
        members = members.filter(member_type=member_type)
    if status:
        if status not in CampusMember.Status.values:
            return _json({"reason": "Unknown status."}, status=400)
        members = members.filter(status=status)
    if department:
        members = members.filter(department_code__iexact=department)
    if query:
        members = members.filter(
            Q(full_name__icontains=query) | Q(campus_id__icontains=query)
        )

    rows = [member_summary(member) for member in members.order_by("full_name")[:100]]
    return _json({"count": len(rows), "members": rows})


@require_http_methods(["GET"])
def member_detail_api(request, campus_id):
    """Full source record for one person. Security staff only.

    GET /api/accounts/members/20251MBI049/
    """
    denied = _gate_staff_json(request)
    if denied:
        return denied

    member = (
        CampusMember.objects.select_related("student_profile", "staff_profile")
        .filter(campus_id__iexact=campus_id)
        .first()
    )
    if member is None:
        return _json({"reason": "No campus record matches this ID."}, status=404)
    return _json(member_source(member))
