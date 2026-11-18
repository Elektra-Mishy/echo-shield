"""
ECHO-SHIELD anomaly detector.

Every place has its own idea of "normal". A smooth tarmac road barely shakes a phone,
while a rough murram road shakes it all the time. So instead of one fixed shock limit,
we learn the typical vibration level of each grid cell from the readings phones send
while moving, and ask: how many times stronger than normal is this shock?
"""
from statistics import median

from .models import BaselineSample

DEFAULT_BASELINE = 1.5   # typical vibration (m/s²) when a place has no learned baseline yet
MIN_SAMPLES = 10         # normal readings a cell needs before we trust its own baseline
RECENT_SAMPLES = 200     # only the most recent normal readings are used
ANOMALY_RATIO = 6.0      # a shock must be at least this many times stronger than normal
MIN_PEAK = 8.0           # and at least this strong in absolute terms (m/s²)


def baseline_level(cell_id):
    """Typical vibration level of this cell, and whether it was learned (True) or the default (False)."""
    values = list(
        BaselineSample.objects.filter(cell_id=cell_id).values_list("rms", flat=True)[:RECENT_SAMPLES]
    )
    if len(values) >= MIN_SAMPLES:
        return max(median(values), 0.3), True
    return DEFAULT_BASELINE, False


def assess_shock(cell_id, peak):
    """Returns (strength compared with normal, is_anomaly, baseline_was_learned)."""
    level, learned = baseline_level(cell_id)
    strength = peak / level
    is_anomaly = strength >= ANOMALY_RATIO and peak >= MIN_PEAK
    return round(strength, 2), is_anomaly, learned