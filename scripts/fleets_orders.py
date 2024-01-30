from datetime import datetime, timedelta, time

from django.utils import timezone

from app.models import Payments
from app.uber_sync import UberRequest


def run():
    first = datetime(2023, 12, 10)
    Payments.objects.filter(report_from__gte=first).delete()



 