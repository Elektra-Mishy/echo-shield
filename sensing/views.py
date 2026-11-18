import json
from datetime import timedelta

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .anomaly import assess_shock
from .models import BaselineSample, Device, Report
from .trust import score_cell

MAX_NORMAL_RMS = 8.0      # a "normal" vibration reading above this is rejected, it is a shock not baseline
KEEP_BASELINE = 300       # how many recent normal readings we keep per cell


def cell_center(cell_id):
    """Turn a cell id like -682_34766 back into the latitude and longitude of the cell's centre."""
    size = settings.GRID_SIZE_DEG
    row, col = cell_id.split("_")
    return (int(row) + 0.5) * size, (int(col) + 0.5) * size


@csrf_exempt
@require_POST
def report_api(request):
    """A phone sends one shock reading. Only shocks that are unusual for that place are kept."""
    try:
        data = json.loads(request.body)
        device_id = str(data["device_id"])[:64]
        fingerprint = str(data.get("fingerprint", ""))[:128]
        lat = float(data["latitude"])
        lng = float(data["longitude"])
        magnitude = float(data["magnitude"])
    except (ValueError, KeyError, TypeError):
        return JsonResponse(
            {"error": "Send JSON with device_id, latitude, longitude and magnitude."}, status=400
        )

    if not (-90 <= lat <= 90 and -180 <= lng <= 180 and 0 <= magnitude <= 200):
        return JsonResponse({"error": "Values out of range."}, status=400)

    # The fingerprint is set when a device first appears and is never changed after that
    device, _ = Device.objects.get_or_create(device_id=device_id, defaults={"fingerprint": fingerprint})

    cell_id = Report.make_cell_id(lat, lng)
    strength, is_anomaly, learned = assess_shock(cell_id, magnitude)

    # A shock that is normal for this place is not an anomaly, so it is not stored as a report
    if is_anomaly:
        Report.objects.create(
            device=device, latitude=lat, longitude=lng, magnitude=magnitude, anomaly=strength
        )

    result = score_cell(cell_id)
    result.update({"accepted": is_anomaly, "anomaly": strength, "baseline_learned": learned})
    return JsonResponse(result)


@csrf_exempt
@require_POST
def baseline_api(request):
    """A moving phone sends a normal-vibration reading. These teach the system what normal feels like."""
    try:
        data = json.loads(request.body)
        lat = float(data["latitude"])
        lng = float(data["longitude"])
        rms = float(data["rms"])
    except (ValueError, KeyError, TypeError):
        return JsonResponse({"error": "Send JSON with latitude, longitude and rms."}, status=400)

    if not (-90 <= lat <= 90 and -180 <= lng <= 180 and 0 <= rms <= MAX_NORMAL_RMS):
        return JsonResponse({"error": "Values out of range."}, status=400)

    cell_id = Report.make_cell_id(lat, lng)
    BaselineSample.objects.create(cell_id=cell_id, rms=rms)

    # Keep only the most recent readings for this cell
    keep = list(BaselineSample.objects.filter(cell_id=cell_id).values_list("id", flat=True)[:KEEP_BASELINE])
    BaselineSample.objects.filter(cell_id=cell_id).exclude(id__in=keep).delete()

    return JsonResponse({"cell_id": cell_id, "samples": BaselineSample.objects.filter(cell_id=cell_id).count()})


@require_GET
def cells_api(request):
    """All cells that have recent reports, each with its trust score. The dashboard reads this."""
    since = timezone.now() - timedelta(seconds=settings.REPORT_WINDOW_SECONDS)
    cell_ids = (
        Report.objects.filter(created_at__gte=since)
        .order_by()
        .values_list("cell_id", flat=True)
        .distinct()
    )
    cells = []
    for cell_id in cell_ids:
        result = score_cell(cell_id)
        result["latitude"], result["longitude"] = cell_center(cell_id)
        cells.append(result)
    return JsonResponse({"window_seconds": settings.REPORT_WINDOW_SECONDS, "cells": cells})


# Where each demo scenario happens on the map
DEMO_SPOTS = {
    "real": (-0.6817, 34.7666),   # Kisii town
    "fake": (-0.6917, 34.7766),
    "bot": (-0.6717, 34.7566),
}


@csrf_exempt
@require_POST
def demo_api(request, scenario):
    """Fires a demo scenario into the real trust engine. Only works while DEBUG is on."""
    if not settings.DEBUG:
        return JsonResponse({"error": "Demo mode is off."}, status=404)

    if scenario == "clear":
        Report.objects.all().delete()
        Device.objects.filter(device_id__startswith="demo-").delete()
        return JsonResponse({"message": "Map cleared."})

    if scenario not in DEMO_SPOTS:
        return JsonResponse({"error": "Unknown scenario."}, status=404)

    lat, lng = DEMO_SPOTS[scenario]
    # Remove this scenario's earlier demo phones so clicking twice does not pile up
    Device.objects.filter(device_id__startswith=f"demo-{scenario}-").delete()

    if scenario == "real":
        for i in range(1, 6):
            d = Device.objects.create(device_id=f"demo-real-{i}", fingerprint=f"demo-fp-{i}", reliability=0.8)
            Report.objects.create(device=d, latitude=lat, longitude=lng, magnitude=15 + i)
    elif scenario == "fake":
        d = Device.objects.create(device_id="demo-fake-1", fingerprint="demo-fp-fake", reliability=0.4)
        Report.objects.create(device=d, latitude=lat, longitude=lng, magnitude=31)
    else:
        for i in range(1, 7):
            d = Device.objects.create(device_id=f"demo-bot-{i}", fingerprint="demo-clone", reliability=0.4)
            Report.objects.create(device=d, latitude=lat, longitude=lng, magnitude=22)

    return JsonResponse(score_cell(Report.make_cell_id(lat, lng)))