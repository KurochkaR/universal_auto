from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from app.models import RawGPS, GPS, Vehicle, VehicleGPS
from app.uagps_sync import UaGpsSynchronizer
from auto.tasks import logger
from scripts.conversion import convertion


def run():
    gps = UaGpsSynchronizer.objects.get(partner=1, deleted_at=None)
    gps.check_today_rent()
