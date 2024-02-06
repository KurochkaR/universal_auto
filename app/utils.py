from django.core.exceptions import ObjectDoesNotExist
from django_celery_beat.models import CrontabSchedule, PeriodicTask


def get_schedule(schema_time, day='*', periodic=None):
    hours, minutes = schema_time.hour, schema_time.minute
    if periodic:
        if hours == "00":
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
    task_args = [partner, param] if param else [partner]
    try:
        periodic_task = PeriodicTask.objects.get(
            name=f'auto.tasks.{task}({task_args})',
            task=f'auto.tasks.{task}',
            queue="beat_tasks"
        )
        if periodic_task.crontab != schedule:
            periodic_task.crontab = schedule
            periodic_task.save()
    except ObjectDoesNotExist:
        PeriodicTask.objects.create(
            name=f'auto.tasks.{task}({task_args})',
            task=f'auto.tasks.{task}',
            queue="beat_tasks",
            crontab=schedule,
            args=task_args
        )
