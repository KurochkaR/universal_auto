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
    fleet = Fleet.objects.filter(partner=1).exclude(name='Gps')
    for f in fleet:
        driver_efficiency = DriverEfficiencyFleet.objects.filter(fleet_id=f.id)
        for efficiency in driver_efficiency:
            driver_canceled_orders = FleetOrder.objects.filter(driver=efficiency.driver,
                                                               date_order__date=efficiency.report_from.date(),
                                                               fleet=f.name,
                                                               state=FleetOrder.DRIVER_CANCEL).count()

            efficiency.total_orders_rejected = driver_canceled_orders
            efficiency.save(update_fields=['total_orders_rejected'])
        print('Done', f.name)
    print('Done all fleets')

    driver_efficiency = DriverEfficiency.objects.all()
    for efficiency in driver_efficiency:
        driver_canceled_orders = FleetOrder.objects.filter(driver=efficiency.driver,
                                                           date_order__date=efficiency.report_from.date(),
                                                           state=FleetOrder.DRIVER_CANCEL).count()

        efficiency.total_orders_rejected = driver_canceled_orders
        efficiency.save(update_fields=['total_orders_rejected'])

    print('Done all drivers')

    DriverPayments.objects.update(salary=F('cash') + F('earning'))

    print('Done all drivers payments')
