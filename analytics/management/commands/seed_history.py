from django.core.management.base import BaseCommand

from analytics.training import seed_history

from ._guard import require_local_db


class Command(BaseCommand):
    help = "Fetch Kigali weather (Open-Meteo) and build synthetic hourly gate history for training."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=180)
        parser.add_argument("--allow-remote", action="store_true")

    def handle(self, *args, **options):
        require_local_db(options["allow_remote"])
        count = seed_history(options["days"])
        self.stdout.write(self.style.SUCCESS(f"Stored {count} synthetic hours of gate traffic."))
