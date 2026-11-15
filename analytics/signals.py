"""Score every new visitor registration as it arrives.

When the desk later approves or rejects the visit, the real outcome is stored
next to the prediction so the dashboard can report live accuracy.
"""

import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from gatepass.models import VisitorVisit

from .models import ModelVersion, VisitPrediction

log = logging.getLogger(__name__)

OUTCOMES = {
    VisitorVisit.Status.APPROVED: VisitPrediction.Outcome.APPROVED,
    VisitorVisit.Status.CHECKED_IN: VisitPrediction.Outcome.APPROVED,
    VisitorVisit.Status.COMPLETED: VisitPrediction.Outcome.APPROVED,
    VisitorVisit.Status.REJECTED: VisitPrediction.Outcome.REJECTED,
}


@receiver(post_save, sender=VisitorVisit, dispatch_uid="analytics_score_visit")
def score_visit_on_save(sender, instance, created, raw=False, **kwargs):
    if raw:
        return
    try:
        with transaction.atomic():
            if created:
                from .ml import active_version, score_visit

                if active_version(ModelVersion.Kind.VISIT_RISK) is not None:
                    score_visit(instance)
            elif instance.status in OUTCOMES:
                VisitPrediction.objects.filter(visit=instance, actual_outcome="").update(
                    actual_outcome=OUTCOMES[instance.status]
                )
    except Exception:
        # A scoring failure must never block a visitor from registering.
        log.exception("Could not score visit %s", instance.reference_number)
