from datetime import datetime, timedelta
from _decimal import Decimal, ROUND_HALF_UP
from django.db.models import Sum, F
from django.db.models.functions import TruncWeek
from django.utils import timezone

from app.models import CarEfficiency, InvestorPayments, Investor, Vehicle, PaymentsStatus, PartnerEarnings, \
    SummaryReport, Schema
from app.uber_sync import UberRequest
from auto.utils import get_currency_rate


def run(*args):
    yesterday = timezone.localtime() - timedelta(days=2)

    UberRequest.objects.get(partner=1).get_fleet_orders(yesterday, yesterday)