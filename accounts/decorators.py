from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .roles import user_can_manage_gate


def gate_staff_required(view):
    """Allow security officers, administrators, and the superuser."""

    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not user_can_manage_gate(request.user):
            return render(request, "accounts/forbidden.html", status=403)
        return view(request, *args, **kwargs)

    return wrapper
