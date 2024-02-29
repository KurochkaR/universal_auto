from datetime import timedelta, datetime, time
from django.utils import timezone

from app.models import DriverReshuffle, BonusCategory, PenaltyCategory, DriverPayments
from app.uagps_sync import UaGpsSynchronizer
from auto.tasks import calculate_vehicle_earnings
from auto_bot.handlers.driver_manager.utils import get_failed_income
from auto_bot.handlers.order.utils import check_vehicle


def run(*args):
    end = timezone.make_aware(datetime.combine(timezone.localtime(), time.min))
    start = end - timedelta(days=7)
    gps = UaGpsSynchronizer.objects.get(partner=1)
    # params = gps.get_params_for_report(gps.get_timestamp(start), gps.get_timestamp(end), 66635, gps.get_session())
    # gps.generate_report(params)
    gps.get_road_distance(start, end, 1)


