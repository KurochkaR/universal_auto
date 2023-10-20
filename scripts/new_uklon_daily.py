from django_celery_beat.models import PeriodicTasks, CrontabSchedule, PeriodicTask

from app.models import TaskScheduler, Partner
from auto.celery import app
from auto.tasks import update_driver_status
from auto_bot.handlers.driver_manager.utils import get_daily_report
from selenium_ninja.bolt_sync import BoltRequest


def run(*args):
    for db_task in TaskScheduler.objects.all():
        hours = f"*/{db_task.task_time.strftime('%H')}" if db_task.periodic else db_task.task_time.strftime('%H')
        minutes = db_task.task_time.strftime('%M')
        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute=minutes,
            hour=hours,
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
        )

        for partner in Partner.objects.all():
            print(partner)
            periodic_task, created = PeriodicTask.objects.get_or_create(
                name=f'auto.tasks.{db_task.name}({partner.pk})',
                task=f'auto.tasks.{db_task.name}',
            )
            print(periodic_task)
            print(created)
            periodic_task.crontab = schedule
            if created:
                periodic_task.args = partner.pk
            periodic_task.save()

