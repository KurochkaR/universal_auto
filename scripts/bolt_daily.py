from datetime import timedelta, datetime
from decimal import Decimal

from django.db.models import Sum, F
from django.db.models.functions import Coalesce
from django.utils import timezone

from app.bolt_sync import BoltRequest
from app.models import DriverReshuffle, BonusCategory, PenaltyCategory, DriverPayments, PenaltyBonus, Payments, \
    CustomReport, Vehicle, FleetOrder, UberSession, ParkSettings
from auto.tasks import calculate_vehicle_earnings, download_weekly_report
from auto.utils import calendar_weekly_report
from auto_bot.handlers.driver_manager.utils import get_failed_income
from auto_bot.handlers.order.utils import check_vehicle
from auto_bot.main import bot
from taxi_service.utils import get_start_end


def run(*args):
    start, end, format_start, format_end = get_start_end('last_week')
    message = calendar_weekly_report(1, start, end, format_start, format_end)
    bot.send_message(chat_id=ParkSettings.get_value('DEVELOPER_CHAT_ID'), text=message)
