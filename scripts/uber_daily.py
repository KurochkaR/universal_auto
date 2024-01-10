from datetime import datetime, timedelta
from _decimal import Decimal, ROUND_HALF_UP
from django.db.models import Sum
from django.db.models.functions import TruncWeek
from app.models import CarEfficiency, InvestorPayments, Investor, Vehicle
from auto.utils import get_currency_rate


def run(*args):
    driver_earning = datetime(2023, 12, 31)
    records = CarEfficiency.objects.filter(report_from__lt=driver_earning)
    weekly_aggregates = records.annotate(
        week_start=TruncWeek('report_from'),
    ).values(
        'week_start'
    ).annotate(
        total=Sum('total_kasa'),
    ).order_by('week_start')
    for aggregate in weekly_aggregates:
        report_from = aggregate['week_start'].date()
        report_to = report_from + timedelta(days=6)
        for investor in Investor.objects.filter(investors_partner=1):
            vehicles = Vehicle.objects.filter(investor_car=investor)
            if vehicles.exists():
                vehicle_kasa = aggregate['total'] / vehicles.count()
                for vehicle in vehicles:
                    currency = vehicle.currency_back
                    earning = vehicle_kasa * Decimal(0.33)
                    if currency != Vehicle.Currency.UAH:
                        rate = get_currency_rate(currency)
                        amount_usd = float(earning) / rate
                        car_earnings = Decimal(str(amount_usd)).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
                    else:
                        car_earnings = earning
                        rate = 0.00
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