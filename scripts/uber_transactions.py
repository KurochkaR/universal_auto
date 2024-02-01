from datetime import datetime, timedelta, time

from _decimal import Decimal
from django.db.models import Sum
from django.db.models.functions import TruncWeek
from django.utils import timezone

from app.models import SummaryReport, Driver, DriverPayments, PaymentsStatus, PartnerEarnings
from app.uklon_sync import UklonRequest


def run():
    start = timezone.make_aware(datetime.combine(timezone.localtime() - timedelta(days=1), time.min))
    end = timezone.make_aware(datetime.combine(timezone.localtime() - timedelta(days=1), time.max))

    UklonRequest.objects.get(partner=1).get_fleet_orders(start, end, 22, "77f5aa6e-e9b1-41a7-966a-424b17b0e873")

