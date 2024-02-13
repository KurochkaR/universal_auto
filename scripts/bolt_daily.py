from datetime import timedelta
from django.utils import timezone

from app.bolt_sync import BoltRequest
from app.uagps_sync import UaGpsSynchronizer
from selenium_ninja.driver import SeleniumTools


def run(*args):
    UaGpsSynchronizer.objects.get(partner=1).create_template()
    # token = SeleniumTools(1).create_gps_session('Микита', 'f76R5F85*6', "https://gps.antenor.online/")