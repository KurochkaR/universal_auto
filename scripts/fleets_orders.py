from datetime import datetime, timedelta

from django.db.models import Prefetch

from auto.tasks import get_orders_from_fleets
from app.models import FleetOrder, FleetsDriversVehiclesRate, DriverPayments, Penalty, Bonus


def run():
    payment = DriverPayments.objects.filter(id=1184).first()
    payment.get_bonuses()


 