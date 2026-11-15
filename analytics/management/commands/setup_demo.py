from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand

from accounts.roles import ADMINISTRATOR, SECURITY_OFFICER

from ._guard import require_local_db


class Command(BaseCommand):
    help = "One command: migrate, load sample data, train the models, and simulate today's traffic."

    def add_arguments(self, parser):
        parser.add_argument("--allow-remote", action="store_true")
        parser.add_argument("--no-simulate", action="store_true")

    def handle(self, *args, **options):
        require_local_db(options["allow_remote"])
        step = lambda text: self.stdout.write(self.style.MIGRATE_HEADING(f"\n▶ {text}"))  # noqa: E731

        step("Database tables")
        call_command("migrate", verbosity=0)
        step("Sample campus, members, and gate records")
        call_command("load_sample_campus")
        call_command("seed_members")
        step("Demo accounts")
        users = get_user_model()
        accounts = [("admin", "admin12345", ADMINISTRATOR, True), ("officer", "officer12345", SECURITY_OFFICER, False)]
        for username, password, group, superuser in accounts:
            if users.objects.filter(username=username).exists():
                self.stdout.write(f"  {username}: already exists (password unchanged)")
                continue
            user = users.objects.create_user(username, password=password, is_staff=superuser, is_superuser=superuser)
            user.groups.add(Group.objects.get_or_create(name=group)[0])
            self.stdout.write(f"  {username} / {password}  ({group})")
        step("Weather (Open-Meteo) and synthetic gate history")
        call_command("seed_history")
        step("Train models from the API")
        call_command("train_models")
        if not options["no_simulate"]:
            step("Simulate today's arrivals")
            call_command("simulate_gate", count=15, decide=True, seed=1)
        self.stdout.write(self.style.SUCCESS(
            "\nReady. Run `python manage.py runserver` and open http://127.0.0.1:8000/dashboard/insights/"
        ))
