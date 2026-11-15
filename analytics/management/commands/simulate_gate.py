"""Feed new incoming data into the system so predictions appear live."""

import random
import time

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import CampusMember, CheckIn
from analytics import synthetic
from analytics.data import features_for
from analytics.models import VisitPrediction
from gatepass.models import GateEvent, VisitorVisit

from ._guard import require_local_db


class Command(BaseCommand):
    help = "Simulate visitors registering and people entering the gate."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=10, help="Visitor registrations to create.")
        parser.add_argument("--interval", type=float, default=0, help="Seconds between arrivals (0 = all at once).")
        parser.add_argument("--members", type=int, default=None, help="Campus member entries (default 3x count).")
        parser.add_argument("--decide", action="store_true", help="Let the 'desk' approve or reject most visits.")
        parser.add_argument("--seed", type=int, default=None)
        parser.add_argument("--allow-remote", action="store_true")

    def handle(self, *args, **options):
        require_local_db(options["allow_remote"])
        rng = random.Random(options["seed"])
        officer, created = get_user_model().objects.get_or_create(
            username="gate-simulator", defaults={"is_active": False}
        )
        if created:
            officer.set_unusable_password()
            officer.save()
        members = list(CampusMember.objects.filter(status=CampusMember.Status.ACTIVE))
        member_entries = options["members"] if options["members"] is not None else options["count"] * 3

        for i in range(options["count"]):
            raw = synthetic.visitor(rng, timezone.now())
            raw.pop("created_at")
            visit = VisitorVisit.objects.create(**raw)
            prediction = VisitPrediction.objects.filter(visit=visit).first()
            score = f"{prediction.percent}% · {prediction.get_risk_level_display()}" if prediction else "not scored"
            line = f"{visit.reference_number}  {visit.full_name:<18} → {visit.destination:<34} {score}"

            if options["decide"] and rng.random() < 0.8:
                approve = rng.random() < synthetic.approval_probability(features_for(visit))
                visit.status = VisitorVisit.Status.APPROVED if approve else VisitorVisit.Status.REJECTED
                visit.save(update_fields=["status"])
                if approve and rng.random() < 0.8:
                    GateEvent.objects.create(visit=visit, event_type=GateEvent.EventType.ENTRY,
                                             officer=officer, outcome=GateEvent.Outcome.ACCEPTED)
                    visit.status = VisitorVisit.Status.CHECKED_IN
                    visit.save(update_fields=["status"])
                line += f"  desk: {'approved' if approve else 'rejected'}"
            self.stdout.write(line)

            if members:
                for _ in range(member_entries // max(options["count"], 1)):
                    CheckIn.objects.create(member=rng.choice(members), status=CheckIn.Status.APPROVED,
                                           approved_at=timezone.now())
            if options["interval"] and i < options["count"] - 1:
                time.sleep(options["interval"])
        self.stdout.write(self.style.SUCCESS(f"Simulated {options['count']} visitors."))
