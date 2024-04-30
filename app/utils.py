import json

from django.core.exceptions import ObjectDoesNotExist
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
