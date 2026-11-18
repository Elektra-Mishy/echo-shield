"""
ECHO-SHIELD trust engine.

Looks at the recent reports in one grid cell and decides how far to trust them.
Trust score (0 to 100) = 45% independent sources + 25% time clustering + 30% device reliability.
Reports from phones that share one fingerprint count as a single source, so a bot swarm cannot fake agreement.
The result also says what "normal" vibration is in this cell and how strong the strongest shock was.
"""
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .anomaly import baseline_level
from .models import Report


def score_cell(cell_id):
    window = settings.REPORT_WINDOW_SECONDS
    since = timezone.now() - timedelta(seconds=window)
    reports = list(
        Report.objects.filter(cell_id=cell_id, created_at__gte=since).select_related("device")
    )
    count = len(reports)
    level, learned = baseline_level(cell_id)

    if count == 0:
        return {
            "cell_id": cell_id, "reports": 0, "independent_sources": 0,
            "agreement": 0.0, "clustering": 0.0, "reliability": 0.0,
            "score": 0, "state": "normal",
            "baseline": round(level, 2), "baseline_learned": learned,
            "strongest_shock": 0.0, "times_normal": 0.0,
        }

    # How many truly different devices agree (cloned fingerprints count once)
    sources = {r.device.fingerprint or r.device.device_id for r in reports}
    independent = len(sources)
    agreement = min(1.0, independent / 4)

    # How close together in time the reports are (needs at least 2 independent sources)
    times = [r.created_at.timestamp() for r in reports]
    spread = max(times) - min(times)
    clustering = 0.0 if independent < 2 else max(0.0, 1 - spread / window)

    # Average track record of the devices that reported
    reliability = sum(r.device.reliability for r in reports) / count

    score = round(100 * (0.45 * agreement + 0.25 * clustering + 0.30 * reliability))

    if score >= 70:
        state = "high-risk"
    elif score >= 40:
        state = "suspicious"
    else:
        state = "rejected"

    strongest = max(r.magnitude for r in reports)

    return {
        "cell_id": cell_id, "reports": count, "independent_sources": independent,
        "agreement": round(agreement, 2), "clustering": round(clustering, 2),
        "reliability": round(reliability, 2), "score": score, "state": state,
        "baseline": round(level, 2), "baseline_learned": learned,
        "strongest_shock": round(strongest, 1), "times_normal": round(strongest / level, 1),
    }