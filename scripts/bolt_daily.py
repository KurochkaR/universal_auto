from datetime import datetime

import requests
from django.db.models import Q
from django.utils import timezone

from app.bolt_sync import BoltRequest
from app.models import Driver, FleetOrder
from app.ninja_sync import NinjaFleet
from app.uagps_sync import UaGpsSynchronizer
from auto_bot.handlers.driver_manager.utils import get_time_for_task


def run(*args):
    driver = Driver.objects.get(pk=22)
    end, start = get_time_for_task(driver.schema_id)[1:3]
    gps = UaGpsSynchronizer.objects.get(partner=1)
    gps.get_non_order_message(start, end, driver)