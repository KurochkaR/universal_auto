from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from app.models import RawGPS, GPS, Vehicle, VehicleGPS
from app.uagps_sync import UaGpsSynchronizer
from auto.tasks import logger
from scripts.conversion import convertion


def run():
    raw_list = RawGPS.objects.filter(vehiclegps__isnull=True).count()
    print(raw_list)
