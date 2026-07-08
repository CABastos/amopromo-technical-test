from django.urls import path

from flight.api import SearchFlightsView

app_name = "flight"

urlpatterns = [
    path("search/", SearchFlightsView.as_view(), name="search"),
]
