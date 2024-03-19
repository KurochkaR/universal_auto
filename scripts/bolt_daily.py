from datetime import timedelta, datetime, time
from django.utils import timezone

from app.bolt_sync import BoltRequest
from app.models import DriverReshuffle, BonusCategory, PenaltyCategory, DriverPayments, PenaltyBonus, Fleet, Driver, \
    FleetsDriversVehiclesRate
from auto.tasks import calculate_vehicle_earnings, download_weekly_report
from auto_bot.handlers.driver_manager.utils import get_failed_income
from auto_bot.handlers.order.utils import check_vehicle


def run(*args):
    fleets = Fleet.objects.filter(
        fleetsdriversvehiclesrate__driver=26, deleted_at=None)
    print(fleets)