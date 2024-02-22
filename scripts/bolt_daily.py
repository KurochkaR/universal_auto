from datetime import timedelta
from django.utils import timezone

from app.models import DriverReshuffle, BonusCategory, PenaltyCategory, DriverPayments
from app.uagps_sync import UaGpsSynchronizer
from auto.tasks import calculate_vehicle_earnings
from auto_bot.handlers.driver_manager.utils import get_failed_income
from auto_bot.handlers.order.utils import check_vehicle


def run(*args):
    end = timezone.localtime()
    start = end - timedelta(days=1)
    UaGpsSynchronizer.objects.get(partner=1).get_road_distance(start, end, 1)

    for order in orders:
        param.append(order.time)
    report = genegate_wialon_report_batch(param)
    for result in report
        #i need update order.distance = result[0] order.road_time = result[1]
# how can i map orders from first loop with results from second
