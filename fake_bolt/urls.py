from django.urls import path
from fake_bolt.views import bolt_login, daily_bolt, DailyWeeklyBoltView, weekly_bolt

urlpatterns = [
    path('login/', bolt_login, name='bolt-login'),
    path('company/58225/reports/dayly/', daily_bolt, name='bolt-daily'),
    path('company/58225/reports/dayly/<str:date_str>/', DailyWeeklyBoltView.as_view(), name='daily-report'),
    path('company/58225/reports/weekly/', weekly_bolt, name='bolt-weekly'),
    path('company/58225/reports/weekly/<str:date_str>/', DailyWeeklyBoltView.as_view(), name='weekly-report'),

]