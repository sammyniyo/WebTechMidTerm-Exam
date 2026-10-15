from django.contrib.auth.views import redirect_to_login
from functools import wraps

from django.core.exceptions import PermissionDenied
from django.shortcuts import resolve_url


def gate_staff_required(view_func):
    """Allow only active staff users to access a gate or campus staff view."""

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return redirect_to_login(
                request.get_full_path(),
                resolve_url("accounts:login"),
            )

        if not user.is_active or not user.is_staff:
            raise PermissionDenied

        return view_func(request, *args, **kwargs)

    return _wrapped_view