from django.core.exceptions import ObjectDoesNotExist
from django_celery_beat.models import CrontabSchedule, PeriodicTask


def get_schedule(hours, minutes, day='*'):

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
            name=f'auto.tasks.{task}({partner})',
            task=f'auto.tasks.{task}',
            queue="beat_tasks"
        )
        if periodic_task.crontab != schedule:
            periodic_task.crontab = schedule
            periodic_task.save()
    except ObjectDoesNotExist:
        task_args = [partner, param] if param else [partner]
        PeriodicTask.objects.create(
            name=f'auto.tasks.{task}({partner})',
            task=f'auto.tasks.{task}',
            queue="beat_tasks",
            crontab=schedule,
            args=task_args
        )
