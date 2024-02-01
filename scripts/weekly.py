import time
from datetime import datetime, timedelta

from django.db.models import F

from app.models import FleetOrder
from auto.tasks import download_daily_report, get_car_efficiency, get_driver_efficiency, get_orders_from_fleets


def run(partner_id=1):
    FleetOrder.objects.all().update(date_order=F("accepted_time__date"))
