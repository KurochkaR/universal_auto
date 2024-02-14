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
            name=f'{task}({partner})',
            task=f'auto.tasks.{task}',
            crontab=schedule,
            queue="beat_tasks"
        )
        args_list = periodic_task.args
        if param and param not in args_list[1]:
            args_list[1].append(param)
            periodic_task.args = args_list
            periodic_task.save(update_fields=['args'])

    except ObjectDoesNotExist:
        task_args = [partner]
        if param:
            task_args.append([param])
        PeriodicTask.objects.create(
            name=f'auto.tasks.{task}({partner})',
            task=f'auto.tasks.{task}',
            queue="beat_tasks",
            crontab=schedule,
            args=task_args
        )
