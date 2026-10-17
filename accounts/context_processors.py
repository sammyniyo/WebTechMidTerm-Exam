from .roles import GATE_GROUPS, user_can_manage_gate


def gate_access(request):
    user = request.user
    role = ""
    if getattr(user, "is_authenticated", False):
        if user.is_superuser:
            role = "Superuser"
        else:
            group = user.groups.filter(name__in=GATE_GROUPS).first()
            role = group.name if group else ""
    return {
        "can_manage_gate": user_can_manage_gate(user),
        "gate_role": role,
    }
