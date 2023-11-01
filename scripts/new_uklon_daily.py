from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone

from app.models import Payments, CustomReport
from auto.tasks import download_daily_report, generate_payments, generate_summary_report, get_car_efficiency, \
    send_efficiency_report
from selenium_ninja.bolt_sync import BoltRequest


def run(*args):
    send_efficiency_report.delay(1)
