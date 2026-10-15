from django.shortcuts import render

from .forms import VisitorRegistrationForm


def visitor_register(request):
    visit = None
    if request.method == "POST":
        form = VisitorRegistrationForm(request.POST)
        if form.is_valid():
            visit = form.save()
    else:
        form = VisitorRegistrationForm()
    return render(
        request,
        "gatepass/register.html",
        {"form": form, "visit": visit},
    )
