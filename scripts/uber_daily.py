from datetime import datetime, timedelta, time

from django.utils import timezone

from auto.tasks import check_daily_report


def run(*args):
    today = timezone.localtime()
    start = timezone.make_aware(datetime.combine(today - timedelta(days=5), time.min))
    end = timezone.make_aware(datetime.combine(start, time.max))
    check_daily_report(1, start, end)