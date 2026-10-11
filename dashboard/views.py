from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def home(request):
    """Placeholder until the AdminLTE dashboard is built."""
    return render(request, "dashboard/index.html")
