from auto.celery import app
from auto.tasks import update_driver_status
from auto_bot.handlers.driver_manager.utils import get_daily_report
from selenium_ninja.bolt_sync import BoltRequest


def run(*args):
    print(app.conf)
