from datetime import timedelta, datetime, time
from django.utils import timezone

from app.bolt_sync import BoltRequest
from app.models import DriverReshuffle, BonusCategory, PenaltyCategory, DriverPayments, PenaltyBonus, Fleet, Driver
from auto.tasks import calculate_vehicle_earnings, download_weekly_report
from auto_bot.handlers.driver_manager.utils import get_failed_income
from auto_bot.handlers.order.utils import check_vehicle


def run(*args):
    start = timezone.make_aware(datetime.combine(timezone.localtime(), time.min))
    fleets = Fleet.objects.filter(partner=1, deleted_at=None).exclude(name__in=['Gps', 'Uber'])
    for fleet in fleets:
        driver_ids = Driver.objects.get_active(
             fleetsdriversvehiclesrate__fleet=fleet).values_list(
            'fleetsdriversvehiclesrate__driver_external_id', flat=True)
        fleet.save_daily_custom(start, timezone.localtime(), driver_ids)