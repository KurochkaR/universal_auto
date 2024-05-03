import json

from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django_celery_beat.models import CrontabSchedule, PeriodicTask


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


def generate_stats_message(
        driver, kasa, card,  distance, orders, canceled_orders, accepted_times, rent_distance, road_time, end_time,
        start_reshuffle):
    time_now = timezone.localtime(end_time)
    if kasa and distance:
        return f"<b>{driver}</b> \n" \
               f"<u>Звіт з {start_reshuffle} по {time_now.strftime('%H:%M')}</u> \n\n" \
               f"Початок роботи: {accepted_times}\n" \
               f"Каса: {round(kasa, 2)}\n" \
               f"Готівка: {round((kasa - card), 2)}\n" \
               f"Виконано замовлень: {orders}\n" \
               f"Скасовано замовлень: {canceled_orders}\n" \
               f"Пробіг під замовленням: {distance}\n" \
               f"Ефективність: {round(kasa / (distance + rent_distance), 2)}\n" \
               f"Холостий пробіг: {rent_distance}\n" \
               f"Час у дорозі: {road_time}\n\n"
    else:
        return f"Водій {driver} ще не виконав замовлень\n" \
               f"Холостий пробіг: {rent_distance}\n\n"
