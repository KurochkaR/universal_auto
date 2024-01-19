from datetime import datetime, timedelta
from _decimal import Decimal, ROUND_HALF_UP
from django.db.models import Sum, F
from django.db.models.functions import TruncWeek
from app.models import CarEfficiency, InvestorPayments, Investor, Vehicle, PaymentsStatus, PartnerEarnings, \
    SummaryReport, Schema
from auto.utils import get_currency_rate


def run(*args):
    pass