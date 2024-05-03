from datetime import datetime

from django.db.models import Q
from django.utils import timezone

from app.models import Driver, DriverPayments, FleetOrder, Fleet, Partner
from app.uagps_sync import UaGpsSynchronizer
from auto_bot.handlers.driver_manager.utils import get_time_for_task
from taxi_service.utils import get_dates, get_start_end


def run(*args):
    start = timezone.make_aware(datetime(2024,4,23,0,0,0))
    end = timezone.make_aware(datetime(2024,4,23,23,59,59))
    print(UaGpsSynchronizer.objects.get(partner=1).get_rent_stats(start, end, 41, False))

