from datetime import timedelta, datetime
from django.utils import timezone

from app.bolt_sync import BoltRequest
from app.models import DriverReshuffle, BonusCategory, PenaltyCategory, DriverPayments, PenaltyBonus, Payments, \
    CustomReport, Vehicle, FleetOrder, UberSession, Driver
from auto.tasks import calculate_vehicle_earnings, download_weekly_report
from auto_bot.handlers.driver_manager.utils import get_failed_income
from auto_bot.handlers.order.utils import check_vehicle


def run(*args):
    driver = Driver.objects.get(pk=41)
    print(driver.get_penalties())
