from datetime import datetime, timedelta, time
from _decimal import Decimal, ROUND_HALF_UP
from django.db.models import Sum, F
from django.db.models.functions import TruncWeek, Coalesce
from django.utils import timezone

from app.models import CarEfficiency, InvestorPayments, Investor, Vehicle, PaymentsStatus, PartnerEarnings, Fleet, \
    Driver, Payments, DriverEfficiencyFleet
from auto.utils import get_currency_rate, polymorphic_efficiency_create, get_efficiency_info
from auto_bot.handlers.driver_manager.utils import get_time_for_task


def run(partner_pk=1):
    start_date = datetime(2023, 12, 1)
    end_date = datetime(2024, 1, 30)
    while start_date <= end_date:
        start_time = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
        end_time = timezone.make_aware(datetime.combine(start_date, datetime.max.time()))
        for driver in Driver.objects.get_active(partner=1):
            aggregators = Fleet.objects.filter(partner=partner_pk).exclude(name="Gps")
            for aggregator in aggregators:
                polymorphic_efficiency_create(DriverEfficiencyFleet, partner_pk, driver,
                                              start_time, end_time, Payments, aggregator)

        start_date += timedelta(days=1)