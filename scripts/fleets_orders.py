from datetime import datetime, timedelta
from auto.tasks import get_orders_from_fleets
from app.models import FleetOrder


def run():
    start = datetime.now() - timedelta(days=60)
    orders = FleetOrder.objects.filter(fleet="Uklon", accepted_time__gte=start, state=FleetOrder.COMPLETED)
    for order in orders:
        try:
            if order.price / order.distance < 10:
                print(order.id)
        except:
            pass


 