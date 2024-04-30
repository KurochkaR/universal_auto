from datetime import datetime

from django.db.models import Q
from django.utils import timezone

from app.models import Driver, DriverPayments, FleetOrder, Fleet
from app.uagps_sync import UaGpsSynchronizer
from auto_bot.handlers.driver_manager.utils import get_time_for_task
from taxi_service.utils import get_dates, get_start_end


def run(*args):
    driver = Driver.objects.get(pk=21)



    start, end = get_dates('last_week')
    print(start, end)