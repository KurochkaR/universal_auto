from datetime import timedelta
from django.utils import timezone

from app.models import DriverReshuffle, BonusCategory, PenaltyCategory, DriverPayments, PenaltyBonus
from auto.tasks import calculate_vehicle_earnings
from auto_bot.handlers.driver_manager.utils import get_failed_income
from auto_bot.handlers.order.utils import check_vehicle


def run(*args):
    payments = DriverPayments.objects.all()

    for payment in payments:
        penalties_bonuses = PenaltyBonus.objects.filter(driver_payments=payment)
        for penalty_bonus in penalties_bonuses:
            penalty_bonus.created_at = payment.report_from
            penalty_bonus.save()
