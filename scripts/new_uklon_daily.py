from datetime import timedelta

from django.utils import timezone
from selenium_ninja.bolt_sync import BoltRequest


def run(*args):
    day = timezone.localtime() - timedelta(days=1)
    BoltRequest(4).save_report(day)

