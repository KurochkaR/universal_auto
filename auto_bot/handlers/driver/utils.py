from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.utils import timezone

from app.models import FleetOrder, DriverPayments, Fleet, Bonus, Penalty


def generate_detailed_info(payment_id):
    try:
        payment = DriverPayments.objects.get(pk=payment_id)
        start, end, driver = payment.report_from, payment.report_to, payment.driver
        orders = FleetOrder.objects.filter(Q(driver=driver) &
                                           Q(Q(price__gt=0) | Q(tips__gt=0)) &
                                           Q(Q(state=FleetOrder.COMPLETED,
                                               finish_time__range=(start, end)) |
                                             Q(state__in=[FleetOrder.CLIENT_CANCEL, FleetOrder.SYSTEM_CANCEL],
                                               accepted_time__range=(start, end)))).order_by('date_order')

        fleet_map = {"Uklon":  "\U0001F7E1",
                     "Bolt":  "\U0001F7E2",
                     "Uber": "\u26AB"}
        payment_map = {"card": "\U0001F4B3", "cash": "\U0001F4B5"}
        orders_text = " ".join([f"{k} - {v}" for k,v in fleet_map.items()]) + "\n"

        orders_text += "\n".join([
            f"{fleet_map.get(order.fleet)} ({timezone.localtime(order.finish_time).strftime('%d.%m - %H:%M') if order.finish_time else 'Скасований'}) {int(order.price)}" +
            (f"+{order.tips}" if order.tips else "") + f" грн {payment_map.get(order.payment)}"
            for order in orders
        ])
    except ObjectDoesNotExist:
        return
    return orders_text


def generate_detailed_bonus(payment_id):
    try:
        payment = DriverPayments.objects.get(pk=payment_id)
        bonus_penalties = payment.penaltybonus_set.select_related('category').all()
        if bonus_penalties:
            text = ""
            bonuses = [bp for bp in bonus_penalties if isinstance(bp, Bonus)]
            penalties = [bp for bp in bonus_penalties if isinstance(bp, Penalty)]

            if bonuses:
                text += "Бонуси:\n"
                text += "".join(
                    [f"{bonus.category.title}({bonus.vehicle}) - {int(bonus.amount)} грн\n" for bonus in bonuses])
            if penalties:
                text += "Штрафи:\n"
                text += "\n".join(
                    [f"{penalty.category.title}({penalty.vehicle}) - {int(penalty.amount)} грн" for penalty in
                     penalties])
        else:
            text = "Відсутні бонуси і штрафи по цій виплаті"
        return text
    except ObjectDoesNotExist:
        return


