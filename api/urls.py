from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token

from .views import *

urlpatterns = [
    path("token-auth/", obtain_auth_token),
    path('api-auth/', include('rest_framework.urls')),
    path("reports/<str:period>/", SummaryReportListView.as_view()),
    path("car_efficiencies/<str:period>/<int:vehicle>", CarEfficiencyListView.as_view()),
    path("vehicles_info/<str:period>/", CarsInformationListView.as_view()),
    path("investor_info/<str:period>/", InvestorCarsEarningsView.as_view()),
    path("driver_info/", DriverInformationListView.as_view()),
    path("drivers_efficiency/<str:period>/<str:aggregators>/", DriverEfficiencyFleetListView.as_view()),
    path("drivers_efficiency/<str:period>/", DriverEfficiencyListView.as_view()),
    path("reshuffle/<str:period>/", DriverReshuffleListView.as_view()),
    path("driver_payments/<str:status>/", DriverPaymentsListView.as_view()),
    path("not_complete_payments/<str:period>/", NotCompletePayments.as_view())
]
