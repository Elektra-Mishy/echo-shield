import math
from django.conf import settings
from django.db import models


class Device(models.Model):
    """One phone running the ECHO sensor page."""
    device_id = models.CharField(max_length=64, unique=True)
    fingerprint = models.CharField(max_length=128, blank=True)  # used to spot cloned devices
    reliability = models.FloatField(default=0.4)  # 0 to 1 track record, grows when reports are corroborated
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.device_id} (reliability {self.reliability:.2f})"


class Report(models.Model):
    """One shock or anomaly reading sent by a phone."""
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="reports")
    latitude = models.FloatField()
    longitude = models.FloatField()
    magnitude = models.FloatField(help_text="Shock strength in m/s²")
    anomaly = models.FloatField(
        null=True, blank=True,
        help_text="How many times stronger this shock is than normal vibration in this place",
    )
    corroborated = models.BooleanField(
        default=False, help_text="True once another independent device confirmed this report"
    )
    cell_id = models.CharField(max_length=40, db_index=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    @staticmethod
    def make_cell_id(lat, lng):
        size = settings.GRID_SIZE_DEG
        return f"{math.floor(lat / size)}_{math.floor(lng / size)}"

    def save(self, *args, **kwargs):
        self.cell_id = self.make_cell_id(self.latitude, self.longitude)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.device.device_id} in {self.cell_id} ({self.magnitude:.1f} m/s²)"


class BaselineSample(models.Model):
    """A normal-road vibration reading, sent now and then while a phone is moving.
    These teach the system what 'normal' feels like in each place."""
    cell_id = models.CharField(max_length=40, db_index=True)
    rms = models.FloatField(help_text="Average vibration strength over a short window, in m/s²")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.cell_id}: {self.rms:.2f} m/s²"