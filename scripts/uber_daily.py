import uuid
from datetime import datetime, timedelta, time

from django.utils import timezone

from app.uklon_sync import UklonRequest
from auto.tasks import check_daily_report
from scripts.redis_conn import redis_instance


def run(*args):

    uklon = UklonRequest.objects.get(partner=1)
    uklon.get_access_token()