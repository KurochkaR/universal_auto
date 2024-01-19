from datetime import datetime, timedelta
from _decimal import Decimal, ROUND_HALF_UP
from django.db.models import Sum, F
from django.db.models.functions import TruncWeek, Coalesce
from app.models import CarEfficiency, InvestorPayments, Investor, Vehicle, PaymentsStatus, PartnerEarnings, Fleet, \
    Driver, Payments, DriverEfficiencyFleet
from auto.utils import get_currency_rate, polymorphic_efficiency_create, get_efficiency_info
from auto_bot.handlers.driver_manager.utils import get_time_for_task


def run(partner_pk=1):
    start_date = datetime(2023, 10, 1)
    end_date = datetime(2024, 1, 19)
    while start_date <= end_date:
        start_time = datetime.combine(start_date, datetime.min.time())
        end_time = datetime.combine(start_date, datetime.max.time())

        for driver in Driver.objects.get_active(partner=partner_pk):
            aggregators = Fleet.objects.filter(partner=partner_pk).exclude(name="Gps")

            for aggregator in aggregators:
                total_kasa, total_orders, canceled_orders, completed_orders, fleet_orders, payments = get_efficiency_info(
                    partner_pk, driver, start_time, end_time, Payments, aggregator)
                vehicles = fleet_orders.values_list('vehicle', flat=True).distinct()
                mileage = fleet_orders.aggregate(km=Coalesce(Sum('distance'), Decimal(0)))['km']
                data = {
                    'total_kasa': total_kasa,
                    'total_orders': total_orders,
                    'accept_percent': (total_orders - canceled_orders) / total_orders * 100 if total_orders else 0,
                    'average_price': total_kasa / completed_orders if completed_orders else 0,
                    'mileage': mileage,
                    'road_time': fleet_orders.aggregate(
                        road_time=Coalesce(Sum('road_time'), timedelta()))['road_time'],
                    'efficiency': total_kasa / mileage if mileage else 0,
                    'partner_id': partner_pk
                }

                result, created = polymorphic_efficiency_create(DriverEfficiencyFleet, partner_pk, driver, start_time,
                                                                end_time,
                                                                data, aggregator)
                if created:
                    if vehicles:
                        result.vehicles.add(*vehicles)

        start_date += timedelta(days=1)
