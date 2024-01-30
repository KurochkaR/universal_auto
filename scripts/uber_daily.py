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
    fleet = Fleet.objects.filter(partner__pk=1).exclude(name='Gps')
    for f in fleet:
        driver_efficiency = DriverEfficiencyFleet.objects.filter(fleet_id=f.id)
        for driver in driver_efficiency:
            driver_canceled_orders = FleetOrder.objects.filter(driver_id=driver,
                                                               accepted_time__date=driver.report_from.date(),
                                                               fleet=driver.fleet.name,
                                                               state=FleetOrder.DRIVER_CANCEL).count()

            driver.total_orders_rejected = driver_canceled_orders
            driver.save(update_fields=['total_orders_rejected'])
        print('Done', f.name)
    print('Done all fleets')

    driver_efficiency = DriverEfficiency.objects.all()
    for driver in driver_efficiency:
        driver_canceled_orders = FleetOrder.objects.filter(driver_id=driver,
                                                           accepted_time__date=driver.report_from.date(),
                                                           state=FleetOrder.DRIVER_CANCEL).count()

        driver.total_orders_rejected = driver_canceled_orders
        driver.save(update_fields=['total_orders_rejected'])

    print('Done all drivers')

    driver_payments = DriverPayments.objects.all()

    for driver in driver_payments:
        cash = driver.cash
        earning = driver.earning
        driver.salary = cash + earning
        driver.save(update_fields=['salary'])

    print('Done all drivers payments')
