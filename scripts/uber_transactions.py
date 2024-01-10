from datetime import datetime, timedelta

from _decimal import Decimal
from django.db.models import Sum
from django.db.models.functions import TruncWeek

from app.models import SummaryReport, Driver, DriverPayments, PaymentsStatus, PartnerEarnings


def run():
    driver_earning = datetime(2023, 10, 9)
    for driver in Driver.objects.all():
        records = SummaryReport.objects.filter(report_from__lt=driver_earning, driver=driver).exclude(total_amount_without_fee=0.00)
        if records:

            weekly_aggregates = records.annotate(
                week_start=TruncWeek('report_from'),
            ).values(
                'week_start'
            ).annotate(
                total=Sum('total_amount_without_fee'),
                cash=Sum('total_amount_cash')
            ).order_by('week_start')

            # Print or use the aggregated data as needed
            for aggregate in weekly_aggregates:
                report_from = aggregate['week_start'].date()
                report_to = report_from + timedelta(days=6)
                salary = aggregate['total'] * Decimal(0.5) - aggregate['cash']
                partner_income = aggregate['total'] * Decimal(0.17)
                data = {"rent_distance": 0,
                        "rent_price": 6,
                        "kasa": aggregate['total'],
                        "cash": aggregate['cash'],
                        "earning": salary,
                        "rent": 0,
                        "partner_id": 1}
                DriverPayments.objects.get_or_create(report_from=report_from,
                                                     report_to=report_to,
                                                     driver=driver,
                                                     defaults=data)
                PartnerEarnings.objects.get_or_create(
                    report_from=report_from,
                    report_to=report_to,
                    driver=driver,
                    partner=driver.partner,
                    defaults={
                        "status": PaymentsStatus.COMPLETED,
                        "earning": partner_income,
                    }
                )

