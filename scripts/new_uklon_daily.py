from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone

from app.models import Payments, CustomReport, DriverSchemaRate, Partner
from auto.tasks import download_daily_report, generate_payments, generate_summary_report, get_car_efficiency, \
    send_efficiency_report, calculate_driver_reports, download_nightly_report, get_orders_from_fleets
from scripts.settings_for_park import standard_rates
from selenium_ninja.bolt_sync import BoltRequest


def run(*args):
    get_orders_from_fleets(1,3)

