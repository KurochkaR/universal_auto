from datetime import timedelta
from django.utils import timezone

from app.models import DriverReshuffle, BonusCategory, PenaltyCategory, DriverPayments, PenaltyBonus
from auto.tasks import calculate_vehicle_earnings, download_weekly_report
from auto_bot.handlers.driver_manager.utils import get_failed_income
from auto_bot.handlers.order.utils import check_vehicle


def run(*args):
    download_weekly_report(1)
