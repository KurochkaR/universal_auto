from datetime import datetime, timedelta
from _decimal import Decimal, ROUND_HALF_UP
from pprint import pprint

from django.db.models import Sum, F
from django.db.models.functions import TruncWeek
from django.utils import timezone

from app.models import CarEfficiency, InvestorPayments, Investor, Vehicle, PaymentsStatus, PartnerEarnings, \
    SummaryReport, Schema, DriverEfficiency, FleetOrder, DriverEfficiencyFleet, Fleet, DriverPayments
from app.uber_sync import UberRequest
from auto.utils import get_currency_rate


def run(*args):
    driver_earning = datetime(2024, 4, 15)
    records = CarEfficiency.objects.filter(report_from__lt=driver_earning, partner=1)
    weekly_aggregates = records.values('vehicle').annotate(
        week_start=TruncWeek('report_from'),
        total=Sum('total_kasa')
    ).order_by('week_start')
    for aggregate in weekly_aggregates:
        report_from = aggregate['week_start'].date()
        report_to = report_from + timedelta(days=6)
        vehicle = Vehicle.objects.get(pk=aggregate['vehicle'])
        currency = vehicle.currency_back
        earning = aggregate['total'] * vehicle.investor_percentage
        rate = get_currency_rate(vehicle.currency_back)
        amount_usd = float(earning) / rate
        car_earnings = Decimal(str(amount_usd)).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
        InvestorPayments.objects.get_or_create(
            report_from=report_from,
            report_to=report_to,
            vehicle=vehicle,
            investor=vehicle.investor_car,
            partner_id=1,
            defaults={
                "earning": earning,
                "currency": currency,
                "currency_rate": rate,
                "sum_after_transaction": car_earnings})
