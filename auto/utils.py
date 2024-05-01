from datetime import timedelta

import requests
from _decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Sum, DecimalField, Q, Value, F
from django.db.models.functions import Coalesce

from app.bolt_sync import BoltRequest
from app.models import CustomReport, ParkSettings, Vehicle, Partner, Payments, SummaryReport, DriverPayments, Penalty, \
    Bonus, FleetOrder, Fleet, DriverReshuffle, DriverEfficiency, InvestorPayments, WeeklyReport, CarEfficiency, \
    ChargeTransactions, Category
from app.uagps_sync import UaGpsSynchronizer
from app.uber_sync import UberRequest
from auto_bot.handlers.driver_manager.utils import create_driver_payments, get_time_for_task
from auto_bot.handlers.order.utils import check_vehicle
from auto_bot.main import bot
from selenium_ninja.synchronizer import AuthenticationError
from taxi_service.utils import get_start_end


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


def create_charge_penalty(driver, start_day, end_day):
    charge_category, _ = Category.objects.get_or_create(title="Зарядка")
    chargings = ChargeTransactions.objects.filter(start_time__range=(start_day, end_day),
                                                  penalty__isnull=True,
                                                  driver=driver)
    print(chargings)
    for charge in chargings:
        amount = charge.get_penalty_amount()
        Penalty.objects.create(driver=driver, vehicle=charge.vehicle,
                               amount=amount, charge=charge, category_id=charge_category.id)


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
        filter_request &= Q(fleet=aggregator.name)
        payment_request &= Q(fleet=aggregator)
    fleet_orders = FleetOrder.objects.filter(filter_request)
    total_kasa = payments_model.objects.filter(payment_request).aggregate(
        kasa=Coalesce(Sum('total_amount_without_fee'), Decimal(0)))['kasa']
    total_orders = fleet_orders.count()
    canceled_orders = fleet_orders.filter(state=FleetOrder.DRIVER_CANCEL).count()
    completed_orders = fleet_orders.filter(state=FleetOrder.COMPLETED).count()

    return total_kasa, total_orders, canceled_orders, completed_orders, fleet_orders


def polymorphic_efficiency_create(create_model, partner_pk, driver, start, end, get_model, aggregator=None,
                                  road_mileage=None):
    search_query = {'driver': driver, 'report_from': start}
    total_kasa, total_orders, canceled_orders, completed_orders, fleet_orders = get_efficiency_info(
        partner_pk, driver, start, end, get_model, aggregator)
    if aggregator:
        if not total_kasa and not fleet_orders:
            return
        search_query.update({'fleet': aggregator})
        vehicles = fleet_orders.exclude(vehicle__isnull=True).values_list('vehicle', flat=True).distinct()
        mileage = fleet_orders.filter(state=FleetOrder.COMPLETED).aggregate(
            km=Coalesce(Sum('distance'), Decimal(0)))['km']
    else:
        mileage, vehicles = UaGpsSynchronizer.objects.get(
            partner=partner_pk).calc_total_km(driver, start, end)
        if not mileage:
            return
    data = {
        'report_to': end,
        'total_kasa': total_kasa,
        'total_orders': total_orders,
        'total_orders_accepted': completed_orders,
        'total_orders_rejected': canceled_orders,
        'mileage': mileage,
        'efficiency': total_kasa / mileage if mileage else 0,
        'road_time': fleet_orders.filter(state=FleetOrder.COMPLETED).aggregate(
            road_time=Coalesce(Sum('road_time'), timedelta()))['road_time'],
        'average_price': total_kasa / completed_orders if completed_orders else 0,
        'accept_percent': (total_orders - canceled_orders) / total_orders * 100 if total_orders else 0,
        'partner_id': partner_pk,
    }
    if road_mileage:
        rent_mileage = mileage - road_mileage[driver][0] if road_mileage.get(driver) else 0
        data['rent_distance'] = rent_mileage
    result, created = create_model.objects.update_or_create(
        **search_query,
        defaults=data)
    result.vehicles.add(*vehicles)


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


def create_investor_payments(start, end, partner_pk, investors):
    investors_schemas = {
        'share': {
            'vehicles': Vehicle.filter_by_share_schema(investors),
            'method': create_share_investor_earn
        },
        'proportional': {
            'vehicles': Vehicle.filter_by_proportional_schema(investors),
            'method': create_proportional_investor_earn
        },
        'rental': {
            'vehicles': Vehicle.filter_by_rental_schema(investors),
            'method': create_rental_investor_earn
        }
    }

    for schema_type, data in investors_schemas.items():
        vehicles = data['vehicles']
        method = data['method']
        if vehicles.exists() and method:
            method(start, end, vehicles, partner_pk)


def create_share_investor_earn(start, end, vehicles_list, partner_pk):
    drivers = DriverReshuffle.objects.filter(
        swap_vehicle__in=vehicles_list, swap_time__range=(start, end)).values_list(
        'driver_start', flat=True).distinct()
    investors_kasa = CarEfficiency.objects.filter(
        report_to__range=(start, end), vehicle__in=vehicles_list, partner=partner_pk).aggregate(
        total=Sum('total_kasa'))['total']

    fleet = Fleet.objects.filter(partner=partner_pk, name="Bolt", deleted_at=None)
    bonus_kasa = calc_bonus_bolt_from_orders(start, end, fleet.first(), vehicles_list, drivers) if fleet.exists() else 0
    vehicle_kasa = (investors_kasa + bonus_kasa) / vehicles_list.count()
    for vehicle in vehicles_list:
        calc_and_create_earn(start, end, vehicle_kasa, vehicle)


def create_proportional_investor_earn(start, end, vehicles_list, partner_pk):
    bolt_fleet = Fleet.objects.filter(partner=partner_pk, name="Bolt", deleted_at=None)
    for vehicle in vehicles_list:
        drivers = DriverReshuffle.objects.filter(
            swap_vehicle=vehicle, swap_time__range=(start, end)).values_list(
            'driver_start', flat=True).distinct()
        investors_kasa = CarEfficiency.objects.filter(
            report_to__range=(start, end), vehicle=vehicle, partner=partner_pk).aggregate(
            total=Sum('total_kasa'))['total']
        print(investors_kasa)
        bonus_kasa = 0
        if bolt_fleet.exists():
            bonus_kasa = calc_bonus_bolt_from_orders(start, end, bolt_fleet.first(), [vehicle], drivers)
            print(bonus_kasa)
        investors_kasa += Decimal(bonus_kasa)
        calc_and_create_earn(start, end, investors_kasa, vehicle)


def create_rental_investor_earn(start, end, vehicles_list: list, partner_pk: int):
    for vehicle in vehicles_list:
        investors_kasa = vehicle.rental_price
        overall_mileage = CarEfficiency.objects.filter(
            report_to__range=(start, end), vehicle=vehicle, partner=partner_pk).aggregate(
            total=Sum('mileage'))['total']
        if overall_mileage > ParkSettings.get_value("RENT_LIMIT",default=2000, partner=partner_pk):
            investors_kasa += overall_mileage * ParkSettings.get_value("OVERALL_MILEAGE_PRICE", default=2,
                                                                       partner=partner_pk)
        calc_and_create_earn(start, end, investors_kasa, vehicle)


def calc_and_create_earn(start, end, kasa, vehicle):
    earning = Decimal(kasa) * vehicle.investor_percentage
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


def calc_bonus_bolt_from_orders(start, end, fleet: Fleet, vehicles_list: list, drivers_list: list):
    weekly_bonus = WeeklyReport.objects.filter(
        report_from=start, report_to=end, fleet=fleet, driver__in=drivers_list).aggregate(
        kasa=Coalesce(Sum('total_amount_without_fee'), 0, output_field=DecimalField()),
        bonuses=Coalesce(Sum('bonuses'), 0, output_field=DecimalField()),
        compensations=Coalesce(Sum('compensations'), 0, output_field=DecimalField()))
    if weekly_bonus['bonuses']:
        driver_orders = FleetOrder.objects.filter(
            fleet=fleet.name, vehicle__in=vehicles_list,
            accepted_time__range=(start, end), driver__in=drivers_list).aggregate(
            total_price=Coalesce(Sum('price'), 0),
            total_tips=Coalesce(Sum('tips'), 0))
        driver_kasa = driver_orders['total_price'] * (1 - fleet.fees) + driver_orders['total_tips']
        print(driver_kasa)
        print(weekly_bonus)
        bonus_kasa = driver_kasa / (weekly_bonus['kasa'] - weekly_bonus['compensations'] -
                                    weekly_bonus['bonuses']) * weekly_bonus['bonuses']
    else:
        bonus_kasa = 0
    return bonus_kasa


def generate_cash_text(driver, kasa, card, penalties, rent, rent_payment, ratio, rate, enable, rent_enable):
    calc_text = f"Готівка {int(kasa - card)}"
    if penalties:
        calc_text += f" борг {int(penalties)}"
    if rent_payment:
        calc_text += f" холостий пробіг {int(rent_payment)}"
    calc_text += f" / {int(kasa)} = {int((1 - ratio) * 100)}%\n"
    if enable:
        text = f"\U0001F7E2 {driver} система увімкнула отримання замовлень за готівку.\n" + calc_text
    elif rent_enable:
        text = f"\U0001F534 {driver} системою вимкнено готівкові замовлення.\n" \
               f"Причина: холостий пробіг\n" + calc_text + f", перепробіг {int(rent)} км\n"
    else:
        text = f"\U0001F534 {driver} системою вимкнено готівкові замовлення.\n" \
               f"Причина: високий рівень готівки\n" + calc_text
    text += f"Дозволено готівки {rate * 100}%"
    return text
