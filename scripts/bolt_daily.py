from datetime import timedelta, datetime
from django.utils import timezone

from app.bolt_sync import BoltRequest
from app.models import DriverReshuffle, BonusCategory, PenaltyCategory, DriverPayments, PenaltyBonus, Payments, \
    CustomReport, Vehicle, FleetOrder, UberSession
from auto.tasks import calculate_vehicle_earnings, download_weekly_report
from auto_bot.handlers.driver_manager.utils import get_failed_income
from auto_bot.handlers.order.utils import check_vehicle


def run(*args):
    # payment_fields = [f.name for f in Payments._meta.get_fields() if
    #                   f.name not in ['id', 'driverreport_ptr', 'polymorphic_ctype']]
    # payments_to_copy = Payments.objects.filter(report_from__date=datetime(2023, 12, 10), partner=1)
    # for payment in payments_to_copy:
    #     custom_report_entry = CustomReport()
    #     for field_name in payment_fields:
    #         setattr(custom_report_entry, field_name, getattr(payment, field_name))
    #     custom_report_entry.save()

    UberSession.objects.create(
        session='QA.CAESEHTy8N9d4k6CllK6dXqq0xkYtOPfsAYiATEqJDQ5ZGZmYzU0LWU4ZDktNDdiZC1hMWU1LTUyY2UxNjI0MWNiNjJAJ90o8w5INKuhpOO7Ji1MRRo6t-70885TNJmwLt-4ooulI13XGvSH0vrlSgYQBQa3URcfhvpe4Ew6ah6k7JCLnjoBMUIIdWJlci5jb20.kkOiCRpm5ZHmL6qGB53ajXCdPigrffuDxENJH2qEv-k',
        cook_session='1.1712845236430.uMsmlWeiPu9KzrL80Xe2ju2+kJsjZXQdSW180HR7TcQ=',
        uber_uuid='49dffc54-e8d9-47bd-a1e5-52ce16241cb6',
        partner_id=1)
