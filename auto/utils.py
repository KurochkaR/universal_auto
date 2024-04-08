from datetime import timedelta

import requests
from _decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Sum, DecimalField, Q, Value, F
from django.db.models.functions import Coalesce

from app.bolt_sync import BoltRequest
from app.models import CustomReport, ParkSettings, Vehicle, Partner, Payments, SummaryReport, DriverPayments, Penalty, \
    Bonus, FleetOrder, Fleet, DriverReshuffle, DriverEfficiency, InvestorPayments, WeeklyReport
from app.uagps_sync import UaGpsSynchronizer
from auto_bot.handlers.driver_manager.utils import create_driver_payments
from auto_bot.handlers.order.utils import check_vehicle
from auto_bot.main import bot
from selenium_ninja.synchronizer import AuthenticationError


def get_currency_rate(currency_code):
    if currency_code == 'UAH':
        return 1
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
        data["report_to"] = report.last().report_to if report.last().report_to >= end else end
        Payments.objects.update_or_create(report_from=report.first().report_from,
                                          fleet=fleet,
                                          driver=driver,
                                          partner=partner_pk,
                                          defaults=data)


def summary_report_create(start, end, driver, partner_pk):
    payments = Payments.objects.filter(report_to__range=(start, end),
                                       report_to__gt=start,
                                       driver=driver, partner=partner_pk).order_by("report_from")
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


def polymorphic_efficiency_create(create_model, partner_pk, driver, start, end, get_model, aggregator=None,
                                  road_mileage=None):
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
    if create_model == DriverEfficiency:
        rent_mileage = mileage - road_mileage[driver][0] if road_mileage.get(driver) else 0
        data['rent_distance'] = rent_mileage

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
    earnings_bonus = \
        CustomReport.objects.filter(report_from__range=(start_date, end_date), partner=partner_pk).aggregate(
            kasa=Coalesce(Sum('total_amount_without_fee'), Decimal(0)),
            bonus=Coalesce(Sum('bonuses'), Decimal(0))
        )

    total_earnings = earnings_bonus['kasa'] + earnings_bonus['bonus']

    vehicles_count = Vehicle.objects.get_active(partner=partner_pk).count()
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


def create_share_investor_earn(start, end, vehicles_list, partner_pk):
    drivers = DriverReshuffle.objects.filter(
        swap_vehicle__in=vehicles_list, swap_time__range=(start, end)).values_list(
        'driver_start', flat=True).distinct()

    shared_kasa = 0
    bonus_kasa = 0
    fleets = Fleet.objects.filter(partner=partner_pk, deleted_at=None).exclude(name__in=['Gps', 'Ninja'])
    for fleet in fleets:
        orders = FleetOrder.objects.filter(
            state__in=[FleetOrder.COMPLETED, FleetOrder.CLIENT_CANCEL],
            accepted_time__range=(start, end), fleet=fleet.name, vehicle__in=vehicles_list)
        shared_orders = orders.aggregate(
            total_price=Coalesce(Sum('price'), 0),
            total_tips=Coalesce(Sum('tips'), 0))
        if isinstance(fleet, BoltRequest):
            bonus_kasa = calc_bonus_bolt_from_orders(start, end, fleet, orders, drivers)
        shared_kasa += shared_orders['total_price'] * (1 - fleet.fees) + shared_orders['total_tips']
        print(shared_kasa)
    vehicle_kasa = (shared_kasa + bonus_kasa) / vehicles_list.count()
    for vehicle in vehicles_list:
        calc_and_create_earn(start, end, vehicle_kasa, vehicle)


def create_proportional_investor_earn(start, end, vehicles_list, partner_pk):
    fleets = Fleet.objects.filter(partner=partner_pk, deleted_at=None).exclude(name__in=['Gps', 'Ninja'])
    for vehicle in vehicles_list:
        drivers = DriverReshuffle.objects.filter(
            swap_vehicle=vehicle, swap_time__range=(start, end)).values_list(
            'driver_start', flat=True).distinct()
        kasa = 0
        bonus_kasa = 0
        for fleet in fleets:
            orders = FleetOrder.objects.filter(
                state__in=[FleetOrder.COMPLETED, FleetOrder.CLIENT_CANCEL],
                accepted_time__range=(start, end), fleet=fleet.name, vehicle=vehicle)
            kasa_orders = orders.aggregate(
                total_price=Coalesce(Sum('price'), 0),
                total_tips=Coalesce(Sum('tips'), 0))
            if isinstance(fleet, BoltRequest):
                for driver in drivers:
                    bonus_kasa += calc_bonus_bolt_from_orders(start, end, fleet, orders, [driver])
            kasa += kasa_orders['total_price'] * (1 - fleet.fees) + kasa_orders['total_tips'] + bonus_kasa
            print(kasa)
        calc_and_create_earn(start, end, kasa, vehicle)


def calc_and_create_earn(start, end, kasa, vehicle):
    earning = kasa * vehicle.investor_percentage
    rate = get_currency_rate(vehicle.currency_back)
    amount_usd = float(earning) / rate
    car_earnings = Decimal(str(amount_usd)).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
    InvestorPayments.objects.get_or_create(
        report_from=start,
        report_to=end,
        vehicle=vehicle,
        investor=vehicle.investor_car,
        partner_id=vehicle.partner_id,
        defaults={
            "earning": earning,
            "currency": vehicle.currency_back,
            "currency_rate": rate,
            "sum_after_transaction": car_earnings})


def calc_bonus_bolt_from_orders(start, end, fleet, orders, drivers_list):
    weekly_bonus = WeeklyReport.objects.filter(
        report_from=start, report_to=end, fleet=fleet, driver__in=drivers_list).aggregate(
        kasa=Coalesce(Sum('total_amount_without_fee'), 0, output_field=DecimalField()),
        bonuses=Coalesce(Sum('bonuses'), 0, output_field=DecimalField()),
        compensations=Coalesce(Sum('compensations'), 0, output_field=DecimalField()))
    if weekly_bonus['bonuses']:
        driver_orders = orders.filter(driver__in=drivers_list).aggregate(
            total_price=Coalesce(Sum('price'), 0),
            total_tips=Coalesce(Sum('tips'), 0))
        driver_kasa = driver_orders['total_price'] * (1 - fleet.fees) + driver_orders['total_tips']
        bonus_kasa = driver_kasa / (weekly_bonus['kasa'] - weekly_bonus['compensations'] -
                                    weekly_bonus['bonuses']) * weekly_bonus['bonuses']
    else:
        bonus_kasa = 0
    return bonus_kasa
