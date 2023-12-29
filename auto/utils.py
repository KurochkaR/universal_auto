from django.db.models import Sum

from app.models import CustomReport, ParkSettings, Vehicle, Partner, Payments, SummaryReport, DriverPayments, \
    DailyReport, WeeklyReport, Penalty, Bonus
from auto_bot.handlers.driver_manager.utils import create_driver_payments
from auto_bot.main import bot


def compare_reports(fleet, start, end, driver, correction_report, compare_model, partner_pk):
    fields = ("total_rides", "total_distance", "total_amount_cash",
              "total_amount_on_card", "total_amount", "tips",
              "bonuses", "fee", "total_amount_without_fee", "fares",
              "cancels", "compensations", "refunds"
              )
    custom_reports = compare_model.objects.filter(vendor=fleet, report_from__range=(start, end), driver=driver)
    last_report = custom_reports.last()
    for field in fields:
        sum_custom_amount = custom_reports.aggregate(Sum(field))[f'{field}__sum']
        daily_value = getattr(correction_report, field)
        if int(daily_value) != int(sum_custom_amount):
            update_amount = last_report.field + daily_value - sum_custom_amount
            setattr(last_report, field, update_amount)
            bot.send_message(chat_id=ParkSettings.get_value('DEVELOPER_CHAT_ID'),
                             text=f"{fleet.name} перевірочний = {daily_value},"
                                  f"денний = {sum_custom_amount} {driver} {field}")
        else:
            continue
    last_report.save()
    last_payment = Payments.objects.filter(vendor=fleet, report_from=last_report.report_from, driver=driver).last()
    payment_24hours_create(last_payment.report_from, last_payment.report_to, fleet, driver, partner_pk)
    summary_report_create(last_payment.report_from, last_payment.report_to, driver, partner_pk)
    if isinstance(correction_report, DailyReport) and not driver.schema.is_weekly():
        start, end = last_payment.report_from, last_payment.report_to
    elif isinstance(correction_report, WeeklyReport) and driver.schema.is_weekly():
        pass
    else:
        return
    payment = DriverPayments.objects.filter(report_from=start,
                                            report_to=end,
                                            driver=driver)
    if payment.exists():
        data = create_driver_payments(start, end, driver, driver.schema)
        description = f"Корекція з {start} по {end}"
        correction = data['salary'] - payment.salary
        correction_data = {"amount": abs(correction),
                           "driver": driver,
                           "description": description
                           }
        if correction > 0:
            Bonus.objects.create(**correction_data)
        if correction < 0:
            Penalty.objects.create(**correction_data)


def payment_24hours_create(start, end, fleet, driver, partner_pk):
    reports = CustomReport.objects.filter(
        report_from__range=(start, end),
        vendor=fleet,
        driver=driver).values('vehicle').annotate(
        without_fee=Sum('total_amount_without_fee'),
        cash=Sum('total_amount_cash'),
        amount=Sum('total_amount'),
        card=Sum('total_amount_on_card') or 0,
        tips=Sum('tips') or 0,
        bonuses=Sum('bonuses') or 0,
        fee=Sum('fee') or 0,
        fares=Sum('fares') or 0,
        cancels=Sum('cancels') or 0,
        compensations=Sum('compensations'),
        refunds=Sum('refunds') or 0,
        distance=Sum('total_distance') or 0,
        rides=Sum('total_rides'))
    for report in reports:
        auto = Vehicle.objects.get(pk=report["vehicle"]) if report["vehicle"] else None
        data = {
            "total_rides": report["rides"],
            "total_distance": report["distance"],
            "total_amount_cash": report["cash"],
            "total_amount_on_card": report["card"],
            "total_amount": report["amount"],
            "tips": report["tips"],
            "bonuses": report["bonuses"],
            "fares": report["fares"],
            "fee": report["fee"],
            "total_amount_without_fee": report["without_fee"],
            "partner": Partner.objects.get(pk=partner_pk),
            "vehicle": auto
        }
        payment, created = Payments.objects.get_or_create(report_from=start,
                                                          report_to=end,
                                                          vendor=fleet,
                                                          driver=driver,
                                                          partner=partner_pk,
                                                          defaults={**data})
        if not created:
            for key, value in data.items():
                setattr(payment, key, value)
            payment.save()


def summary_report_create(start, end, driver, partner_pk):
    payments = Payments.objects.filter(report_from=start, report_to=end, driver=driver, partner=partner_pk)
    if payments.exists():
        fields = ("total_rides", "total_distance", "total_amount_cash",
                  "total_amount_on_card", "total_amount", "tips",
                  "bonuses", "fee", "total_amount_without_fee", "fares",
                  "cancels", "compensations", "refunds"
                  )
        default_values = {}
        for field in fields:
            default_values[field] = sum(getattr(payment, field, 0) or 0 for payment in payments)
        report, created = SummaryReport.objects.get_or_create(report_from=start,
                                                              report_to=end,
                                                              driver=driver,
                                                              vehicle=driver.vehicle,
                                                              partner_id=partner_pk,
                                                              defaults=default_values)
        if not created:
            for field in fields:
                setattr(report, field, sum(getattr(payment, field, 0) or 0 for payment in payments))
            report.save(update_fields=fields)
