from datetime import datetime, timedelta
from auto.tasks import get_orders_from_fleets
from app.models import FleetOrder, FleetsDriversVehiclesRate


def run():
    pay_cash = FleetsDriversVehiclesRate.objects.filter(driver=41, fleet=45).update(pay_cash=True)
    print(pay_cash)


 