import json

from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django_celery_beat.models import CrontabSchedule, PeriodicTask

from app.models import DriverReshuffle, Driver, FleetOrder, DriverEfficiency
from taxi_service.utils import get_dates


def get_schedule(schema_time, day='*', periodic=None):
    hours, minutes = schema_time.hour, schema_time.minute
    if periodic:
        if not hours:
            minutes = f"*/{minutes}"
            hours = "*"
        else:
            hours = f"*/{hours}"
    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute=minutes,
        hour=hours,
        day_of_week=day,
        day_of_month='*',
        month_of_year='*',
    )
    return schedule


def create_task(task, partner, schedule, param=None):
    try:
        periodic_task = PeriodicTask.objects.get(
            name=f'{task}({partner}_{schedule})',
            task=f'auto.tasks.{task}',
        )
        args_dict = eval(periodic_task.kwargs) if periodic_task.kwargs else {}
        if param:
            if len(args_dict) == 1:
                args_dict.update({"schemas": {param}})
            else:
                args_dict["schemas"].add(param)
            periodic_task.kwargs = json.dumps(args_dict)
            periodic_task.save(update_fields=['kwargs'])

    except ObjectDoesNotExist:
        task_kwargs = {"partner_pk": partner}
        if param:
            task_kwargs.update({"schemas": {param}})
        PeriodicTask.objects.create(
            name=f'{task}({partner}_{schedule})',
            task=f'auto.tasks.{task}',
            crontab=schedule,
            kwargs=json.dumps(task_kwargs)
        )


def generate_efficiency_message(partner):
    text = ""
    start, end = get_dates("today")
    reshuffles = DriverReshuffle.objects.filter(
                partner=partner, swap_time__range=(start, end),
                driver_start__isnull=False)
    driver_in_reshuffle = reshuffles.values_list('driver_start', flat=True)
    drivers = Driver.objects.filter(pk__in=driver_in_reshuffle)
    for driver in drivers:
        start_reshuffle = reshuffles.filter(driver_start=driver).order_by('swap_time').first().swap_time
        orders = FleetOrder.objects.filter(driver=driver,
                                           state=FleetOrder.COMPLETED,
                                           date_order__range=(start, end)).order_by("accepted_time")

        efficiency = DriverEfficiency.objects.filter(driver=driver, report_from=start).first()
        if not orders:
            rent = efficiency.rent_distance if efficiency else 0.00
            text += f"Водій {driver} ще не виконав замовлень\n" \
                    f"Холостий пробіг: {rent}\n\n"
            continue
        start_work = timezone.localtime(orders.first().accepted_time)
        last_order = timezone.localtime(orders.last().finish_time)
        text += f"<b>{driver}</b> \n" \
                f"<u>Звіт з {timezone.localtime(start_reshuffle).strftime('%H:%M')} по {last_order.strftime('%H:%M')}</u> \n\n" \
                f"Початок роботи: {start_work.strftime('%H:%M')}\n" \
                f"Каса: {efficiency.total_kasa}\n" \
                f"Готівка: {efficiency.total_cash}\n" \
                f"Виконано замовлень: {efficiency.total_orders_accepted}\n" \
                f"Скасовано замовлень: {efficiency.total_orders_rejected}\n" \
                f"Пробіг під замовленням: {efficiency.mileage - efficiency.rent_distance}\n" \
                f"Ефективність: {efficiency.efficiency}\n" \
                f"Холостий пробіг: {efficiency.rent_distance}\n" \
                f"Час у дорозі: {efficiency.road_time}\n\n"
    return text
