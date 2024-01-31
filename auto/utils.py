import time
from datetime import timedelta

import requests
from _decimal import Decimal
from django.db.models import Sum, DecimalField, Q
from django.db.models.functions import Coalesce
from django.utils import timezone

from app.models import CustomReport, ParkSettings, Vehicle, Partner, Payments, SummaryReport, DriverPayments, Penalty, \
    Bonus, FleetOrder
from app.uagps_sync import UaGpsSynchronizer
from auto_bot.handlers.driver_manager.utils import create_driver_payments
from auto_bot.handlers.order.utils import check_vehicle
from auto_bot.main import bot
from selenium_ninja.synchronizer import AuthenticationError


def get_currency_rate(currency_code):
    api_url = f'https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode={currency_code}&json'
    response = requests.get(api_url)
    if response.status_code == 200:
        data = response.json()
        return data[0]['rate']
    else:
        raise AuthenticationError(response.json())


def compare_reports(fleet, start, end, driver, correction_report, compare_model, partner_pk):
    fields = ("total_rides", "total_distance", "total_amount_cash",
              "total_amount_on_card", "total_amount", "tips",
              "bonuses", "fee", "total_amount_without_fee", "fares",
              "cancels", "compensations", "refunds"
              )
    message_fields = ("total_amount_cash", "total_amount_without_fee")
    custom_reports = compare_model.objects.filter(fleet=fleet, report_from__range=(start, end), driver=driver)
    if custom_reports:
        last_report = custom_reports.last()
        for field in fields:
            sum_custom_amount = custom_reports.aggregate(Sum(field, output_field=DecimalField()))[f'{field}__sum'] or 0
            daily_value = getattr(correction_report, field) or 0
            if int(daily_value) != int(sum_custom_amount):
                report_value = getattr(last_report, field) or 0
                update_amount = report_value + Decimal(daily_value) - sum_custom_amount
                setattr(last_report, field, update_amount)
                if field in message_fields:
                    bot.send_message(chat_id=ParkSettings.get_value('DEVELOPER_CHAT_ID'),
                                     text=f"{fleet.name} перевірочний = {daily_value},"
                                          f"денний = {sum_custom_amount} {driver} {field}")
            else:
                continue
        last_report.save()
        payment_report = Payments.objects.filter(fleet=fleet, report_from=last_report.report_from, driver=driver)
        if payment_report.exists():
            last_payment = payment_report.last()
            payment_24hours_create(last_payment.report_from, last_payment.report_to, fleet, driver, partner_pk)
            summary_report_create(last_payment.report_from, last_payment.report_to, driver, partner_pk)


def get_corrections(start, end, driver):
    payment = DriverPayments.objects.filter(report_from=start,
                                            report_to=end,
                                            driver=driver)
    if payment.exists():
        data = create_driver_payments(start, end, driver, driver.schema)
        format_start = start.strftime("%d.%m")
        format_end = end.strftime("%d.%m")
        description = f"Корекція з {format_start} по {format_end}"
        correction = Decimal(data['earning']) - payment.first().earning
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
        fleet=fleet,
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
                                                          fleet=fleet,
                                                          driver=driver,
                                                          partner=partner_pk,
                                                          defaults={**data})
        if not created:
            for key, value in data.items():
                setattr(payment, key, value)
            payment.save()


def summary_report_create(start, end, driver, partner_pk):
    payments = Payments.objects.filter(report_from=start, report_to=end, driver=driver, partner=partner_pk)
    vehicle = check_vehicle(driver, date_time=end)
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
                                                              vehicle=vehicle,
                                                              partner_id=partner_pk,
                                                              defaults=default_values)
        if not created:
            for field in fields:
                setattr(report, field, sum(getattr(payment, field, 0) or 0 for payment in payments))
            report.save(update_fields=fields)


def get_efficiency_info(partner_pk, driver, start, end, payments_model, aggregator=None):
    filter_request = Q(driver=driver, accepted_time__range=(start, end), partner_id=partner_pk)

    payment_request = Q(driver=driver, report_from__date=start, partner_id=partner_pk)

    if aggregator:
        filter_request &= Q(fleet=aggregator.name)
        payment_request &= Q(fleet=aggregator)
    fleet_orders = FleetOrder.objects.filter(filter_request)
    total_kasa = payments_model.objects.filter(payment_request).aggregate(
        kasa=Coalesce(Sum('total_amount_without_fee'), Decimal(0)))['kasa']
    total_orders = fleet_orders.count()
    canceled_orders = fleet_orders.filter(state=FleetOrder.DRIVER_CANCEL).count()
    completed_orders = fleet_orders.filter(state=FleetOrder.COMPLETED).count()

    return total_kasa, total_orders, canceled_orders, completed_orders, fleet_orders


def polymorphic_efficiency_create(create_model, partner_pk, driver, start, end, get_model, aggregator=None):
    efficiency_filter = {
                        'report_from': start,
                        'report_to': end,
                        'driver': driver,
                        'partner_id': partner_pk
                         }
    total_kasa, total_orders, canceled_orders, completed_orders, fleet_orders = get_efficiency_info(
        partner_pk, driver, start, end, get_model, aggregator)
    if aggregator:
        if not total_kasa and not fleet_orders:
            return
        vehicles = fleet_orders.exclude(vehicle__isnull=True).values_list('vehicle', flat=True).distinct()
        mileage = fleet_orders.filter(state=FleetOrder.COMPLETED).aggregate(
            km=Coalesce(Sum('distance'), Decimal(0)))['km']
        efficiency_filter['fleet'] = aggregator
    else:
        mileage, vehicles = UaGpsSynchronizer.objects.get(
            partner=partner_pk).calc_total_km(driver, start, end)
        if not mileage:
            return
    data = {
        'total_kasa': total_kasa,
        'total_orders': total_orders,
        'accept_percent': (total_orders - canceled_orders) / total_orders * 100 if total_orders else 0,
        'average_price': total_kasa / completed_orders if completed_orders else 0,
        'mileage': mileage,
        'road_time': fleet_orders.filter(state=FleetOrder.COMPLETED).aggregate(
            road_time=Coalesce(Sum('road_time'), timedelta()))['road_time'],
        'efficiency': total_kasa / mileage if mileage else 0,
        'partner_id': partner_pk
    }
    efficiency_filter['defaults'] = data
    result, created = create_model.objects.get_or_create(**efficiency_filter)
    if created:
        result.vehicles.add(*vehicles)

