"""
Device reliability: how much should we trust this phone, based on its history?

A brand new phone starts at 0.4. Every time another independent phone confirms one of its
reports, it earns trust. Reports that nobody confirms slowly lower it. Only a phone's most
recent reports count, so a phone can recover, and a phone cannot bank trust forever.

reliability = (confirmed reports + 0.4 x 2) / (recent reports + 2)
"""
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import Report

PRIOR = 0.4              # where a brand new device starts
PRIOR_WEIGHT = 2         # the starting value counts as this many imaginary reports
HISTORY = 20             # only a device's most recent reports count
MIN_RELIABILITY = 0.05
MAX_RELIABILITY = 0.95


def update_reliability(device):
    """Recalculate and save one device's reliability from its recent reports."""
    recent = list(device.reports.order_by("-created_at").values_list("corroborated", flat=True)[:HISTORY])
    confirmed = sum(1 for c in recent if c)
    value = (confirmed + PRIOR * PRIOR_WEIGHT) / (len(recent) + PRIOR_WEIGHT)
    device.reliability = round(min(MAX_RELIABILITY, max(MIN_RELIABILITY, value)), 3)
    device.save(update_fields=["reliability"])
    return device.reliability


def credit_corroboration(cell_id):
    """If at least two independent devices have reported in this cell recently, they confirm
    each other: mark the reports as corroborated and update every device involved."""
    since = timezone.now() - timedelta(seconds=settings.REPORT_WINDOW_SECONDS)
    reports = list(
        Report.objects.filter(cell_id=cell_id, created_at__gte=since).select_related("device")
    )
    sources = {r.device.fingerprint or r.device.device_id for r in reports}
    if len(sources) < 2:
        return False   # nobody else agrees, so nothing to credit

    Report.objects.filter(id__in=[r.id for r in reports if not r.corroborated]).update(corroborated=True)
    for device in {r.device for r in reports}:
        update_reliability(device)
    return True