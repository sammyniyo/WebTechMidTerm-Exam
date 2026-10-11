SECURITY_OFFICER = "Security officer"
ADMINISTRATOR = "Administrator"
GATE_GROUPS = (SECURITY_OFFICER, ADMINISTRATOR)


def user_can_manage_gate(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=GATE_GROUPS).exists()
