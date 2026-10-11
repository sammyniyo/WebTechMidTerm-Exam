from django.shortcuts import render

from accounts.decorators import gate_staff_required


@gate_staff_required
def home(request):
    """Placeholder until the AdminLTE dashboard is built."""
    return render(request, "dashboard/index.html")
