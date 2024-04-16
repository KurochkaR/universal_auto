from datetime import datetime

import requests
from django.db.models import Q, Sum
from django.utils import timezone

from app.bolt_sync import BoltRequest
from app.models import Driver, FleetOrder, DriverPayments
from app.ninja_sync import NinjaFleet
from app.uagps_sync import UaGpsSynchronizer
from auto_bot.handlers.driver_manager.utils import get_time_for_task
from taxi_service.utils import get_dates, get_start_end


def run(*args):

    start, end = get_dates('last_week')
    print(start, end)