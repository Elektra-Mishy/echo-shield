from django.urls import path

from . import views

urlpatterns = [
    path("report/", views.report_api, name="report_api"),
    path("baseline/", views.baseline_api, name="baseline_api"),
    path("cells/", views.cells_api, name="cells_api"),
    path("demo/<str:scenario>/", views.demo_api, name="demo_api"),
]