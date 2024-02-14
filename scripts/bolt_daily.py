from datetime import timedelta, datetime, time
from django.utils import timezone

from app.bolt_sync import BoltRequest
from app.uagps_sync import UaGpsSynchronizer
from selenium_ninja.driver import SeleniumTools


def run(*args):
    pass