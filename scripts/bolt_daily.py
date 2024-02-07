from datetime import timedelta
from django.utils import timezone

from auto_bot.handlers.order.utils import check_vehicle


def run(*args):
    print(check_vehicle(22))