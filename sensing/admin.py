from django.contrib import admin

from .models import BaselineSample, Device, Report


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("device_id", "fingerprint", "reliability", "created_at")
    search_fields = ("device_id", "fingerprint")


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("device", "cell_id", "magnitude", "anomaly", "latitude", "longitude", "created_at")
    list_filter = ("cell_id",)


@admin.register(BaselineSample)
class BaselineSampleAdmin(admin.ModelAdmin):
    list_display = ("cell_id", "rms", "created_at")
    list_filter = ("cell_id",)