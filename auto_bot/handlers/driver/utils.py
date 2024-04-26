from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.utils import timezone

from app.models import FleetOrder, DriverPayments, Fleet


def generate_detailed_info(payment_id):
    try:
        payment = DriverPayments.objects.get(pk=payment_id)
        start, end , driver = payment.report_from, payment.report_to, payment.driver
        orders = FleetOrder.objects.filter(Q(driver=driver) &
                                           Q(Q(price__gt=0) | Q(tips__gt=0)) &
                                           Q(Q(state=FleetOrder.COMPLETED,
                                               finish_time__range=(start, end)) |
                                             Q(state__in=[FleetOrder.CLIENT_CANCEL, FleetOrder.SYSTEM_CANCEL],
                                               accepted_time__range=(start, end)))).order_by('date_order')

        fleet_map = {"Uklon": 1 - Fleet.objects.get(name="Uklon", partner=None).fees,
                     "Bolt": 1 - Fleet.objects.get(name="Bolt", partner=None).fees}
        orders_text = "\n".join([
            f"{order.fleet} {timezone.localtime(order.accepted_time).strftime('%d.%m %H:%M')} - {timezone.localtime(order.finish_time).strftime('%H:%M') if order.finish_time else '-'} ціна-{int(order.price * fleet_map.get(order.fleet))}" +
            (f", чайові, компенсації-{order.tips}" if order.tips else "")
            for order in orders
        ])
    except ObjectDoesNotExist:
        return
    return orders_text
