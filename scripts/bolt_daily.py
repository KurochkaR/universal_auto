from datetime import datetime

from django.db.models import Q
from django.utils import timezone

from app.models import Driver, DriverPayments, FleetOrder, Fleet, Partner
from app.uagps_sync import UaGpsSynchronizer
from auto_bot.handlers.driver_manager.utils import get_time_for_task
from taxi_service.utils import get_dates, get_start_end


def run(*args):
    driver = Driver.objects.select_related('schema').get(pk=41)
    print(driver)

