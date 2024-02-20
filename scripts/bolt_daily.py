from datetime import timedelta
from django.utils import timezone

from app.models import DriverReshuffle, BonusCategory, PenaltyCategory, DriverPayments
from auto.tasks import calculate_vehicle_earnings
from auto_bot.handlers.driver_manager.utils import get_failed_income
from auto_bot.handlers.order.utils import check_vehicle


def run(*args):
    payment = DriverPayments.objects.get(id=2579)
    calculate_vehicle_earnings(payment)
