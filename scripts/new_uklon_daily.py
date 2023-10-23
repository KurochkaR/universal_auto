from datetime import timedelta

from django.utils import timezone
from django_celery_beat.models import PeriodicTasks, CrontabSchedule, PeriodicTask

from app.models import TaskScheduler, Partner
from auto.celery import app
from auto.tasks import update_driver_status
from auto_bot.handlers.driver_manager.utils import get_daily_report
from selenium_ninja.bolt_sync import BoltRequest


def run(*args):
    day = timezone.localtime() - timedelta(days=1)
    BoltRequest(4).save_report(day)

