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
            queue=f"beat_tasks_{partner}"
        )
        args_list = eval(periodic_task.args) if periodic_task.args else []
        if param:
            if len(args_list) == 1:
                args_list.append([param])
            if param not in args_list[1]:
                args_list[1].append(param)
            periodic_task.args = str(args_list)
            periodic_task.save(update_fields=['args'])

    except ObjectDoesNotExist:
        task_args = [partner]
        if param:
            task_args.append([param])
        PeriodicTask.objects.create(
            name=f'{task}({partner}_{schedule})',
            task=f'auto.tasks.{task}',
            queue=f"beat_tasks_{partner}",
            crontab=schedule,
            args=task_args
        )
