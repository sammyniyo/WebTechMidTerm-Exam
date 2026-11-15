from django.core.management.base import BaseCommand, CommandError

from analytics import training
from analytics.client import APIError


class Command(BaseCommand):
    help = "Read training data from the analytics API and train both models."

    def add_arguments(self, parser):
        parser.add_argument("--source", choices=["api", "synthetic"], default="api",
                            help="api: read /api/analytics/datasets/ (default). synthetic: generate in memory.")
        parser.add_argument("--api-url", help="Read a running server over HTTP, e.g. http://127.0.0.1:8000")
        parser.add_argument("--token", help="ANALYTICS_API_TOKEN of that server.")

    def handle(self, *args, **options):
        try:
            results = training.run(options["source"], options["api_url"], options["token"], log=self.stdout.write)
        except (APIError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        for record in results.values():
            self.stdout.write(self.style.SUCCESS(f"{record} · {record.data_source}"))
            for key, value in record.metrics.items():
                self.stdout.write(f"    {key}: {value}")
