from datetime import timedelta
from django.utils import timezone

from app.models import DriverReshuffle, BonusCategory, PenaltyCategory
from auto_bot.handlers.order.utils import check_vehicle


def run(*args):
    BonusCategory.objects.create(title="Премія")
