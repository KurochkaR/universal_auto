from datetime import timedelta

import requests
from _decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Sum, DecimalField, Q, Value, F
from django.db.models.functions import Coalesce

from app.models import CustomReport, ParkSettings, Vehicle, Partner, Payments, SummaryReport, DriverPayments, Penalty, \
    Bonus, FleetOrder, Fleet, DriverReshuffle
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


def get_corrections(start, end, driver, driver_reports=None):
    payment = DriverPayments.objects.filter(report_from=start,
                                            report_to=end,
                                            driver=driver)
    if payment.exists():
        data = create_driver_payments(start, end, driver, driver.schema, driver_reports)[0]
        format_start = start.strftime("%d.%m")
        format_end = end.strftime("%d.%m")
        description = f"Корекція з {format_start} по {format_end}"
        correction = Decimal(data['earning']) - payment.first().earning
        correction_data = {"amount": abs(correction),
                           "driver": driver,
                           "description": description
                           }

        Bonus.objects.create(**correction_data) if correction > 0 else Penalty.objects.create(**correction_data)


def payment_24hours_create(start, end, fleet, driver, partner_pk):
    report = CustomReport.objects.filter(
        report_to__range=(start, end),
        fleet=fleet,
        driver=driver).order_by("report_from")
    if report:
        data = report.aggregate(
            total_amount_without_fee=Coalesce(Sum('total_amount_without_fee'), Decimal(0)),
            total_amount_cash=Coalesce(Sum('total_amount_cash'), Decimal(0)),
            total_amount=Coalesce(Sum('total_amount'), Decimal(0)),
            total_amount_on_card=Coalesce(Sum('total_amount_on_card'), Decimal(0)),
            tips=Coalesce(Sum('tips'), Decimal(0)),
            bonuses=Coalesce(Sum('bonuses'), Decimal(0)),
            fee=Coalesce(Sum('fee'), Decimal(0)),
            fares=Coalesce(Sum('fares'), Decimal(0)),
            cancels=Coalesce(Sum('cancels'), Decimal(0)),
            compensations=Coalesce(Sum('compensations'), Decimal(0)),
            refunds=Coalesce(Sum('refunds'), Decimal(0)),
            total_distance=Coalesce(Sum('total_distance'), Decimal(0)),
            total_rides=Coalesce(Sum('total_rides'), Value(0)))
        data["partner"] = Partner.objects.get(pk=partner_pk)
        data["report_to"] = report.last().report_to
        Payments.objects.update_or_create(report_from=report.first().report_from,
                                          fleet=fleet,
                                          driver=driver,
                                          partner=partner_pk,
                                          defaults=data)


def summary_report_create(start, end, driver, partner_pk):
    payments = Payments.objects.filter(report_to__range=(start, end),
                                       report_to__gt=start,
                                       driver=driver, partner=partner_pk).order_by("report_from")
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
        default_values['report_to'] = payments.first().report_to
        report, created = SummaryReport.objects.get_or_create(report_from=payments.first().report_from,
                                                              driver=driver,
                                                              vehicle=vehicle,
                                                              partner=partner_pk,
                                                              defaults=default_values)
        if not created:
            for field in fields:
                setattr(report, field, sum(getattr(payment, field, 0) or 0 for payment in payments))
            report.report_to = payments.first().report_to
            report.save()
        return report


def get_efficiency_info(partner_pk, driver, start, end, payments_model, aggregator=None):
    filter_request = Q(driver=driver, date_order__range=(start, end), partner_id=partner_pk)

    payment_request = Q(driver=driver, report_to__range=(start, end), partner_id=partner_pk)

    if aggregator:
        fleet = Fleet.objects.get(pk=aggregator)
        filter_request &= Q(fleet=fleet.name)
        payment_request &= Q(fleet=fleet)
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
        efficiency_filter['fleet_id'] = aggregator
    else:
        mileage, vehicles = UaGpsSynchronizer.objects.get(
            partner=partner_pk).calc_total_km(driver, start, end)
        if not mileage:
            return
    data = {
        'total_kasa': total_kasa,
        'total_orders': total_orders,
        'total_orders_accepted': completed_orders,
        'total_orders_rejected': canceled_orders,
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
    if not created and any([total_kasa != result.total_kasa,
                            total_orders != result.total_orders,
                            mileage != result.mileage]):
        for key, value in data.items():
            setattr(result, key, value)

        result.save()


def calendar_weekly_report(partner_pk, start_date, end_date, format_start, format_end):
    total_earnings = \
        CustomReport.objects.filter(report_from__range=(start_date, end_date), partner=1).aggregate(
            kasa=Coalesce(Sum('total_amount_without_fee'), Decimal(0)))['kasa']

    vehicles_count = Vehicle.objects.filter(partner=partner_pk).count()
    maximum_working_time = (24 * 7 * vehicles_count) * 3600

    qs_reshuffle = DriverReshuffle.objects.filter(
        swap_time__range=(start_date, end_date),
        end_time__range=(start_date, end_date),
        partner=partner_pk
    )
    total_shift_duration = qs_reshuffle.filter(driver_start__isnull=False).aggregate(
        total_shift_duration=Coalesce(Sum(F('end_time') - F('swap_time')), timedelta(0))
    )['total_shift_duration'].total_seconds()

    occupancy_percentage = (total_shift_duration / maximum_working_time) * 100

    total_accidents = qs_reshuffle.filter(dtp_or_maintenance='accident').aggregate(
        total_accidents_duration=Coalesce(Sum(F('end_time') - F('swap_time')), timedelta(0))
    )['total_accidents_duration'].total_seconds()
    total_accidents_percentage = (total_accidents / maximum_working_time) * 100

    total_maintenance = qs_reshuffle.filter(dtp_or_maintenance='maintenance').aggregate(
        total_maintenance_duration=Coalesce(Sum(F('end_time') - F('swap_time')), timedelta(0))
    )['total_maintenance_duration'].total_seconds()
    total_maintenance_percentage = (total_maintenance / maximum_working_time) * 100

    total_idle = 100 - occupancy_percentage - total_accidents_percentage - total_maintenance_percentage

    message = (
        f"Звіт за період з {format_start} по {format_end}\n\n"
        f"Загальна сума автопарку: {total_earnings}\n"
        f"Кількість авто: {vehicles_count}\n"
        f"Відсоток зайнятості авто: {occupancy_percentage:.2f}%\n"
        f"Кількість простою: {total_idle:.2f}%\n"
        f"Кількість аварій: {total_accidents_percentage:.2f}%\n"
        f"Кількість ТО: {total_maintenance_percentage:.2f}%\n"
    )
    return message
