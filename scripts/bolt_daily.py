import requests

from app.bolt_sync import BoltRequest
from app.models import Driver
from app.ninja_sync import NinjaFleet


def run(*args):
    driver = Driver.objects.get(pk=89)
    print(BoltRequest.objects.get(partner=1).check_driver_status(driver))
