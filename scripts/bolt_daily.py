from datetime import timedelta
from django.utils import timezone

from app.models import DriverReshuffle, BonusCategory, PenaltyCategory, DriverPayments, PenaltyBonus, Driver
from auto.tasks import calculate_vehicle_earnings
from auto_bot.handlers.driver_manager.utils import get_failed_income
from auto_bot.handlers.order.utils import check_vehicle


def run(*args):
    print(Driver.objects.get_active(schema=1).values_list('fleetsdriversvehiclesrate__driver_external_id', flat=True))
