from datetime import datetime, timedelta, time

from django.db.models import Prefetch
from django.utils import timezone

from auto.tasks import get_orders_from_fleets
from app.models import FleetOrder, FleetsDriversVehiclesRate, DriverPayments, Penalty, Bonus


def run():
    for payment in DriverPayments.objects.all():

        time_from = timezone.make_aware(datetime.combine(payment.report_from, time.min))
        time_to = timezone.make_aware(datetime.combine(payment.report_to, time.max))
        payment.report_to = time_to
        payment.report_from = time_from
        payment.save()


 