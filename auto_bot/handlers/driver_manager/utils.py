from collections import defaultdict
from datetime import datetime, timedelta, time

from _decimal import Decimal
from django.db.models import Sum, Avg, DecimalField, ExpressionWrapper, F, Value, Q, Count, Func, Case, When
from django.db.models.functions import Coalesce
from django.utils import timezone
from telegram.error import BadRequest

from app.bolt_sync import BoltRequest
from app.models import CarEfficiency, Driver, SummaryReport, \
    Vehicle, RentInformation, DriverEfficiency, DriverSchemaRate, SalaryCalculation, \
    DriverPayments, FleetOrder, VehicleRent, Schema, Fleet, CustomUser, CustomReport, PaymentTypes, Payments, \
    WeeklyReport, PaymentsStatus, ParkSettings, Manager, PartnerEarnings, Bonus, Category
from auto_bot.handlers.order.utils import check_reshuffle, check_vehicle
from auto_bot.main import bot
from auto_bot.utils import send_long_message
from scripts.redis_conn import get_logger


def format_hours(total_hours):
    total_seconds = int(total_hours.total_seconds()) if total_hours else 0
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def get_start_week_time(start, end):
    start_today = timezone.make_aware(datetime.combine(timezone.localtime(), time.min))
    yesterday = start_today - timedelta(days=1)
    if not start and not end:
        if timezone.localtime().weekday():
            start = start_today - timedelta(days=timezone.localtime().weekday())
        else:
            start = start_today - timedelta(weeks=1)
        end = timezone.make_aware(datetime.combine(yesterday, time.max.replace(microsecond=0)))
    return start, end, yesterday


def get_time_for_task(schema, day=None):
    """
    Returns time periods
    :param schema: pk of the schema
    :param day: report day if needed
    :type schema: int
    :return: start, end, previous_start, previous_end
    """
    schema_obj = Schema.objects.get(pk=schema)
    if schema_obj.shift_time != time.min:
        shift_time = schema_obj.shift_time
        date = datetime.strptime(day, "%Y-%m-%d") if day else timezone.localtime()
        yesterday = date - timedelta(days=1)
    else:
        shift_time = time.max.replace(microsecond=0)
        date = datetime.strptime(day, "%Y-%m-%d") - timedelta(days=1) if day else timezone.localtime() - timedelta(
            days=1)
        yesterday = date
    start = timezone.make_aware(datetime.combine(date, time.min))
    previous_end = timezone.make_aware(datetime.combine(yesterday, time.max.replace(microsecond=0)))
    end = timezone.make_aware(datetime.combine(date, shift_time))
    previous_start = timezone.make_aware(datetime.combine(yesterday, schema_obj.shift_time))
    return start, end, previous_start, previous_end


def find_reshuffle_period(reshuffle, start, end):
    if start > reshuffle.swap_time:
        start_period, end_period = start, reshuffle.end_time
    elif reshuffle.end_time <= end:
        start_period, end_period = reshuffle.swap_time, reshuffle.end_time
    else:
        start_period, end_period = reshuffle.swap_time, end
    return timezone.localtime(start_period), timezone.localtime(end_period)


def add_bonus_earnings(start_week, end_week, driver, bolt_weekly):
    vehicle_bonus = {}
    weekly_reshuffles = check_reshuffle(driver, start_week, end_week)
    for shift in weekly_reshuffles:
        shift_bolt_kasa = calculate_bolt_kasa(driver, shift.swap_time, shift.end_time,
                                              vehicle=shift.swap_vehicle)[0]
        reshuffle_bonus = shift_bolt_kasa / (
                bolt_weekly['kasa'] - bolt_weekly['compensations'] - bolt_weekly['bonuses']) * \
                          bolt_weekly['bonuses']
        if not vehicle_bonus.get(shift.swap_vehicle):
            vehicle_bonus[shift.swap_vehicle] = reshuffle_bonus
        else:
            vehicle_bonus[shift.swap_vehicle] += reshuffle_bonus
    for car, bonus in vehicle_bonus.items():
        amount = bonus * driver.schema.rate
        vehicle_amount = bonus * (1 - driver.schema.rate)
        PartnerEarnings.objects.get_or_create(report_from=start_week,
                                              report_to=end_week,
                                              vehicle=car,
                                              partner=driver.partner,
                                              defaults={
                                                  "status": PaymentsStatus.COMPLETED,
                                                  "earning": vehicle_amount})
        bolt_category = Category.objects.get_or_create(title="Бонуси Bolt")
        Bonus.objects.create(driver=driver, vehicle=car, amount=amount, category=bolt_category)


def create_driver_payments(start, end, driver, schema, bonuses=None, driver_report=None, delete=None):
    reports = SummaryReport.objects.filter(report_to__range=(start, end),
                                           report_to__gt=start,
                                           driver=driver).order_by('-report_from')
    if not driver_report:
        driver_report = reports.aggregate(
            cash=Coalesce(Sum('total_amount_cash'), 0, output_field=DecimalField()),
            kasa=Coalesce(Sum('total_amount_without_fee'), 0, output_field=DecimalField()))
    kasa = driver_report['kasa'] + bonuses if bonuses else driver_report['kasa']
    rent = calculate_rent(start, end, driver)
    rent_value = rent * schema.rent_price
    rate = schema.rate
    if delete:
        salary = '%.2f' % (kasa * rate - driver_report['cash'] - rent_value)
    elif schema.is_dynamic():
        driver_spending = calculate_by_rate(driver, kasa, driver.partner_id)
        salary = '%.2f' % (driver_spending - driver_report['cash'] - rent_value)
        rate = driver_spending / kasa if kasa else 0
    elif schema.is_rent():
        overall_distance = DriverEfficiency.objects.filter(
            report_from__range=(start, end),
            driver=driver).aggregate(
            distance=Coalesce(Sum('mileage'), 0, output_field=DecimalField()))['distance']
        rent = max((overall_distance - schema.limit_distance), 0)
        rent_value = rent * schema.rent_price
        salary = '%.2f' % (kasa * rate -
                           driver_report['cash'] - schema.rental - rent_value)
    elif schema.is_float():
        rate = get_driver_salary_rate(driver, kasa, driver.partner_id)
        salary = '%.2f' % (kasa * rate - driver_report['cash'] - rent_value)
    else:
        salary = '%.2f' % (kasa * rate - driver_report['cash'] - (
            (schema.plan - kasa) * Decimal(1 - schema.rate)
            if kasa < schema.plan else 0) - rent_value
                           )
    if schema.is_weekly():
        report_from = start
        report_to = end
        no_price = False
        status = PaymentsStatus.CHECKING
    else:
        start_schema = timezone.make_aware(datetime.combine(timezone.localtime() - timedelta(days=1),
                                                            schema.shift_time))
        last_payment = DriverPayments.objects.filter(
            driver=driver,
            report_to__date=start_schema).order_by("-report_from").last()
        if last_payment and last_payment.report_to > start_schema:
            report_from = timezone.localtime(last_payment.report_to)
        else:
            report_from = start_schema
        report_to = reports.first().report_to if reports else end
        status, no_price = check_correct_bolt_report(start, end, driver)
    data = {"report_from": report_from,
            "report_to": report_to,
            "rent_distance": rent,
            "rent_price": schema.rent_price,
            "kasa": kasa,
            "cash": driver_report['cash'],
            "earning": salary,
            "rent": rent_value,
            "rate": rate * 100,
            "payment_type": schema.salary_calculation,
            "status": status,
            "partner": schema.partner
            }

    return data, no_price


def check_correct_bolt_report(start, end, driver):
    bolt_order_kasa = calculate_bolt_kasa(driver, start, end)[0]
    bolt_report = CustomReport.objects.filter(
        report_to__range=(start, end),
        report_to__gt=start,
        driver=driver, fleet__name="Bolt").aggregate(
        kasa=Coalesce(Sum('total_amount_without_fee'), 0, output_field=DecimalField()),
        compensations=Coalesce(Sum('compensations'), 0, output_field=DecimalField()),
        bonuses=Coalesce(Sum('bonuses'), 0, output_field=DecimalField()),
    )
    filter_request = Q(Q(fleet="Bolt", driver=driver) &
                       Q(state=FleetOrder.COMPLETED, finish_time__lt=start) |
                       Q(state=FleetOrder.CLIENT_CANCEL, accepted_time__lt=start)
                       )
    no_price = FleetOrder.objects.filter(price=0, state=FleetOrder.COMPLETED, fleet="Bolt",
                                         driver=driver, finish_time__range=(start, end))
    tolerance = 1
    incorrect = round(bolt_order_kasa, 2) - round(
        (bolt_report['kasa'] - bolt_report['compensations']), 2)
    status = PaymentsStatus.INCORRECT if no_price.exists() else PaymentsStatus.CHECKING
    if abs(incorrect) >= tolerance:
        status = PaymentsStatus.INCORRECT
        print(incorrect)
        print(
            f"orders {round(bolt_order_kasa, 2)} kasa {round((bolt_report['kasa'] - bolt_report['compensations']), 2)}")
        print(no_price.exists())
        last_order = FleetOrder.objects.filter(filter_request).order_by('-accepted_time').first()
        incorrect_with_last = round(bolt_order_kasa + Decimal(last_order.price * 0.75004 + last_order.tips), 2) - round(
            (bolt_report['kasa'] - bolt_report['compensations']), 2)
        if incorrect_with_last < tolerance:
            status = PaymentsStatus.CHECKING
    return status, no_price.exists()


def validate_date(date_str):
    try:
        check_date = datetime.strptime(date_str, '%d.%m.%Y')
        today = datetime.today() - timedelta(days=1)
        if check_date > today:
            return False
        else:
            return True
    except ValueError:
        return False


def validate_sum(sum_str):
    try:
        float(sum_str)
        return True
    except (ValueError, TypeError):
        return False


def get_drivers_vehicles_list(chat_id, cls):
    objects = []
    user = CustomUser.get_by_chat_id(chat_id)

    if user.is_manager():
        objects = cls.objects.filter(manager=user.pk)
    elif user.is_partner():
        objects = cls.objects.filter(partner=user.pk)
    return objects, user


def calculate_rent(start, end, driver):
    end_time = timezone.make_aware(datetime.combine(end, datetime.max.time()))
    rent_report = RentInformation.objects.filter(
        rent_distance__gt=driver.schema.limit_distance,
        report_to__range=(start, end_time),
        report_to__gt=start,
        driver=driver)
    overall_rent = ExpressionWrapper(F('rent_distance') - driver.schema.limit_distance,
                                     output_field=DecimalField())
    total_rent = rent_report.aggregate(distance=Sum(overall_rent))['distance'] or 0
    return total_rent


def calculate_daily_reports(start, end, driver):
    kasa = CustomReport.objects.filter(report_from__range=(start, end), driver=driver).aggregate(
        kasa=Coalesce(Sum('total_amount_without_fee'), 0, output_field=DecimalField()))['kasa']

    rent = calculate_rent(start, end, driver)
    return kasa, rent


def calculate_by_rate(driver, kasa, partner):
    rate_tiers = DriverSchemaRate.get_rate_tier(period=driver.schema.salary_calculation,
                                                partner=partner)
    driver_spending = 0
    tier = 0
    rates = rate_tiers[2:] if kasa >= driver.schema.plan else rate_tiers
    for tier_kasa, rate in rates:
        tier_kasa -= tier
        if kasa > tier_kasa:
            driver_spending += tier_kasa * rate
            kasa -= tier_kasa
            tier += tier_kasa
        else:
            driver_spending += kasa * rate
            break
    return driver_spending


def get_driver_salary_rate(driver, kasa, partner):
    rate_tiers = DriverSchemaRate.get_rate_tier(period=driver.schema.salary_calculation,
                                                partner=partner)
    for tier_kasa, rate in rate_tiers:
        if kasa < tier_kasa:
            return rate
    return driver.schema.rate


def get_daily_report(manager_id, schema_obj=None):
    drivers = get_drivers_vehicles_list(manager_id, Driver)[0]
    if schema_obj:
        report_time = timezone.make_aware(datetime.combine(timezone.localtime().date(), schema_obj.shift_time))
        drivers = drivers.filter(schema=schema_obj)
    else:
        report_time = timezone.localtime()
        drivers = drivers.filter(schema__isnull=False)
    end = report_time - timedelta(days=1)
    start = report_time - timedelta(days=report_time.weekday()) if report_time.weekday() else \
        report_time - timedelta(weeks=1)

    total_values = {}
    day_values = {}
    rent_daily = {}
    total_rent = {}
    for driver in drivers:
        daily_report = calculate_daily_reports(end, end, driver)
        day_values[driver], rent_daily[driver] = daily_report
        total_report = calculate_daily_reports(start, end, driver)
        total_values[driver], total_rent[driver] = total_report
    sort_report = dict(sorted(total_values.items(), key=lambda item: item[1], reverse=True))
    return sort_report, day_values, total_rent, rent_daily


def generate_message_report(chat_id, schema_id=None, daily=None):
    drivers, user = get_drivers_vehicles_list(chat_id, Driver)
    drivers = drivers.filter(schema__isnull=False).select_related('schema')
    if schema_id:
        schema = Schema.objects.get(pk=schema_id)
        if schema.salary_calculation == SalaryCalculation.WEEK:
            if not timezone.localtime().weekday():
                end = timezone.localtime() - timedelta(days=timezone.localtime().weekday() + 1)
                start = end - timedelta(days=6)
            else:
                return
        else:
            end, start = get_time_for_task(schema_id)[1:3]
        drivers = drivers.filter(schema=schema)
    elif daily:
        start = end = timezone.localtime() - timedelta(days=1)
    else:
        end = timezone.localtime() - timedelta(days=timezone.localtime().weekday() + 1)
        start = end - timedelta(days=6)
    message = ''
    drivers_dict = {}
    balance = 0
    payments = DriverPayments.objects.filter(
        report_from__date=start, report_to__date=end, driver__in=drivers).select_related('driver', "driver__schema")
    for payment in payments:
        if payment.driver.deleted_at in (start, end):
            driver_message = f"{payment.driver} каса: {payment.kasa}\n" \
                             f"Зарплата {payment.kasa} - Готівка {payment.cash}" \
                             f" - Холостий пробіг {payment.rent} = {payment.earning}\n"
        else:
            driver_message = message_driver_report(payment)
            balance += payment.kasa - payment.earning - payment.cash
            message += driver_message

        if driver_message:
            message += "*" * 39 + '\n'
    if message and user:
        manager_message = "Звіт з {0} по {1}\n".format(start.date(), end.date())
        manager_message += f'Ваш баланс:%.2f\n' % balance
        manager_message += message
        drivers_dict[user.chat_id] = manager_message
    return drivers_dict


def message_driver_report(payment):
    driver = payment.driver
    schema = payment.driver.schema
    weekly_bolt = WeeklyReport.objects.filter(
        report_from=payment.report_from, report_to=payment.report_to, driver=driver).aggregate(
        bonuses=Coalesce(Sum('bonuses'), Decimal(0)))['bonuses']
    reports = Payments.objects.filter(
        driver=driver,
        report_from__range=(payment.report_from, payment.report_to)).values('fleet__name').annotate(
        fleet_kasa=Coalesce(Sum('total_amount_without_fee'), Decimal(0)),
        fleet_cash=Coalesce(Sum('total_amount_cash'), Decimal(0)))
    driver_message = (f"<b>{driver}</b>\n<u>Виплата з {timezone.localtime(payment.report_from).strftime('%d.%m %H:%M')}"
                      f" по {timezone.localtime(payment.report_to).strftime('%d.%m %H:%M')}</u>\n")
    driver_message += f"Загальна каса: {payment.kasa}\n"
    for report in reports:
        if report['fleet__name'] == "Bolt" and weekly_bolt:
            driver_message += f"Бонуси {report['fleet__name']}: {weekly_bolt}\n"
        driver_message += f"{report['fleet__name']} каса: {report['fleet_kasa']} готівка: {report['fleet_cash']}\n"
    if payment.rent:
        driver_message += "Холостий пробіг: {0} * {1} = {2}\n".format(
            payment.rent_distance, payment.rent_price, payment.rent)
    if schema.is_rent():
        driver_message += 'Зарплата {0} * {1} - Готівка {2} - Абонплата {3}'.format(
            payment.kasa, schema.rate, payment.cash, schema.rental)
    elif schema.is_dynamic():
        driver_message += 'Зарплата {0} - Готівка {1}'.format(
            payment.earning + payment.cash + payment.rent, payment.cash)
    elif schema.is_float():
        rate = get_driver_salary_rate(driver, payment.kasa, driver.partner.id)
        driver_message += 'Зарплата {0} * {1} - Готівка {2}'.format(
            payment.kasa, rate, payment.cash, payment.rent)
    else:
        driver_message += 'Зарплата {0} * {1} - Готівка {2}'.format(
            payment.kasa, schema.rate, payment.cash)
        if payment.kasa < schema.plan:
            incomplete = (schema.plan - payment.kasa) * Decimal(1 - schema.rate)
            driver_message += " - План {:.2f}".format(incomplete)

    bonuses = payment.get_bonuses()
    penalties = payment.get_penalties()
    if bonuses:
        driver_message += " + Бонуси: {0}".format(bonuses)
    if penalties:
        driver_message += " - Штрафи: {0}".format(penalties)
    if payment.rent:
        driver_message += f" - Холостий пробіг {payment.rent}"
    driver_message += f" = {payment.earning}\n"

    return driver_message


def generate_report_period(chat_id, start, end):
    message = ''
    balance = 0

    drivers, user = get_drivers_vehicles_list(chat_id, Driver)
    for driver in drivers:
        payment = DriverPayments.objects.filter(report_to__range=(start, end),
                                                driver=driver).values('driver_id').annotate(
            period_kasa=Sum('kasa') or 0,
            period_cash=Sum('cash') or 0,
            period_rent_distance=Sum('rent_distance') or 0,
            period_salary=Sum('earning') or 0,
            period_rent=Sum('rent') or 0
        )
        if payment:
            payment = payment[0]
            driver_message = f"{driver}\n" \
                             f"Каса: {payment['period_kasa']}\n" \
                             f"Готівка: {payment['period_cash']}\n" \
                             f"Холостий пробіг: {payment['period_rent_distance']}км, {payment['period_rent']}грн\n" \
                             f"Зарплата: {payment['period_salary']}\n\n"
            balance += payment['period_kasa'] - payment['period_salary'] - payment['period_cash']
            message += driver_message
    manager_message = "Звіт з {0} по {1}\n".format(start.date(), end.date())
    manager_message += f'Ваш баланс: %.2f\n' % balance
    manager_message += message

    return manager_message


def calculate_efficiency(vehicle, start, end):
    efficiency_objects = CarEfficiency.objects.filter(report_from__range=(start, end),
                                                      vehicle=vehicle)
    vehicle_drivers = []
    driver_kasa_totals = defaultdict(float)
    for obj in efficiency_objects:
        drivers = obj.drivers.all().values_list('user_ptr__name', 'user_ptr__second_name', 'drivereffvehiclekasa__kasa')

        for first_name, second_name, kasa in drivers:
            driver_key = (first_name, second_name)
            driver_kasa_totals[driver_key] += float(kasa)
    driver_info = [f"{first_name} {second_name} ({total_kasa:.2f})" for
                   (first_name, second_name), total_kasa in driver_kasa_totals.items()]
    vehicle_drivers.extend(driver_info)
    total_kasa = efficiency_objects.aggregate(kasa=Coalesce(Sum('total_kasa'), Decimal(0)))['kasa']
    total_distance = efficiency_objects.aggregate(total_distance=Coalesce(Sum('mileage'), Decimal(0)))['total_distance']
    efficiency = float('{:.2f}'.format(total_kasa / total_distance)) if total_distance else 0
    formatted_distance = float('{:.2f}'.format(total_distance)) if total_distance is not None else 0.00
    return efficiency, formatted_distance, total_kasa, vehicle_drivers


def get_efficiency(manager_id=None, start_time=None, end_time=None):
    start, end, yesterday = get_start_week_time(start_time, end_time)
    effective_vehicle = {}
    report = {}
    vehicles = get_drivers_vehicles_list(manager_id, Vehicle)[0]
    for vehicle in vehicles:
        effect = calculate_efficiency(vehicle, start, end)
        yesterday_effect = calculate_efficiency(vehicle, yesterday, end)
        drivers = ", ".join(effect[3])
        if end.date() == yesterday.date() and yesterday_effect:
            effective_vehicle[vehicle.licence_plate] = {
                'Водії': drivers,
                'Середня ефективність(грн/км)': effect[0],
                'Ефективність(грн/км)': yesterday_effect[0],
                'Пробіг (км)': f"{effect[1]} ({yesterday_effect[1]})",
                'Каса (грн)': f"{effect[2]} (+{yesterday_effect[2]})",
            }
        else:
            effective_vehicle[vehicle.licence_plate] = {
                'Водії': drivers,
                'Середня ефективність(грн/км)': effect[0],
                'Пробіг (км)': effect[1],
                'Каса (грн)': effect[2]}
    sorted_effective_driver = dict(sorted(effective_vehicle.items(),
                                          key=lambda x: x[1]['Середня ефективність(грн/км)'],
                                          reverse=True))
    for k, v in sorted_effective_driver.items():
        report[k] = [f"{vk}: {vv}\n" for vk, vv in v.items()]
    return report


def calculate_efficiency_driver(driver, start, end):
    efficiency_objects = DriverEfficiency.objects.filter(report_from__range=(start, end), driver=driver)
    if efficiency_objects.exists():
        annotated_efficiency = efficiency_objects.aggregate(
            total_eff_orders=Sum('total_orders'),
            completed_orders=Sum('total_orders_accepted'),
            total_distance=Sum('mileage'),
            total_hours=Sum('road_time'),
            total_rent=Sum('rent_distance'),
            total_eff_kasa=Sum('total_kasa'))
        accept_eff_percent = 100 if annotated_efficiency['total_eff_orders'] == 0 else (
                (annotated_efficiency['completed_orders'] / annotated_efficiency['total_eff_orders']) * 100
        )

        avg_price = 0 if annotated_efficiency['completed_orders'] == 0 else (
                annotated_efficiency['total_eff_kasa'] / annotated_efficiency['completed_orders']
        )

        efficiency_avg = 0 if annotated_efficiency['total_distance'] == 0 else (
                annotated_efficiency['total_eff_kasa'] / annotated_efficiency['total_distance']
        )
        vehicles = list(efficiency_objects.values_list('vehicles__licence_plate', flat=True).distinct())

        annotated_efficiency['accept_eff_percent'] = '{:.2f}'.format(accept_eff_percent)
        annotated_efficiency['avg_price'] = '{:.2f}'.format(avg_price)
        annotated_efficiency['efficiency_avg'] = '{:.2f}'.format(efficiency_avg)
        annotated_efficiency['vehicles'] = vehicles

        return annotated_efficiency


def get_driver_efficiency_report(manager_id, start_time=None, end_time=None):
    start, end, yesterday = get_start_week_time(start_time, end_time)
    drivers = get_drivers_vehicles_list(manager_id, Driver)[0]
    drivers = drivers.filter(schema__isnull=False)
    effective_driver = {}
    report = {}
    for driver in drivers:
        effect = calculate_efficiency_driver(driver, start, end)
        yesterday_effect = calculate_efficiency_driver(driver, yesterday, end)
        if effect:
            licence_plates = ', '.join(effect['vehicles'])
            total_hours_formatted = format_hours(effect['total_hours'])
            if end.date() == yesterday.date() and yesterday_effect:
                car_plates = ', '.join(yesterday_effect['vehicles'])
                yesterday_hours_formatted = format_hours(yesterday_effect['total_hours'])
                effective_driver[driver] = {
                    'Автомобілі': f"{licence_plates} ({car_plates})",
                    'Каса': f"{effect['total_eff_kasa']} (+{yesterday_effect['total_eff_kasa']}) грн",
                    'Холостий пробіг': f"{effect['total_rent']} (+{yesterday_effect['total_rent']}) км",
                    'Ефективність': f"{effect['efficiency_avg']} (+{yesterday_effect['efficiency_avg']}) грн/км",
                    'Виконано замовлень': f"{effect['completed_orders']} (+{yesterday_effect['completed_orders']})",
                    '% прийнятих': f"{effect['accept_eff_percent']} ({yesterday_effect['accept_eff_percent']})",
                    'Cередній чек': f"{effect['avg_price']} ({yesterday_effect['avg_price']}) грн",
                    'Пробіг': f"{effect['total_distance']} (+{yesterday_effect['total_distance']}) км",
                    'Час в дорозі': f"{total_hours_formatted}(+{yesterday_hours_formatted})"
                }
            else:
                effective_driver[driver] = {
                    'Автомобілі': f"{licence_plates}",
                    'Каса': f"{effect['total_eff_kasa']} грн",
                    'Холостий пробіг': f"{effect['total_rent']} км",
                    'Ефективність': f"{effect['efficiency_avg']} грн/км",
                    'Виконано замовлень': f"{effect['completed_orders']}",
                    '% прийнятих': f"{effect['accept_eff_percent']}",
                    'Cередній чек': f"{effect['avg_price']} грн",
                    'Пробіг': f"{effect['total_distance']} км",
                    'Час в дорозі': f"{total_hours_formatted}"
                }
    sorted_effective_driver = dict(sorted(effective_driver.items(),
                                          key=lambda x: float(x[1]['Каса'].split()[0]),
                                          reverse=True))
    for k, v in sorted_effective_driver.items():
        report[k] = [f"{vk}: {vv}\n" for vk, vv in v.items()]
    return report, start, end


def calculate_bolt_kasa(driver, start_period, end_period, vehicle=None):
    filter_request = Q(Q(fleet="Bolt", driver=driver) &
                       Q(state=FleetOrder.COMPLETED, finish_time__range=(start_period, end_period)) |
                       Q(state=FleetOrder.CLIENT_CANCEL, accepted_time__range=(start_period, end_period))
                       )
    if vehicle:
        filter_request &= Q(vehicle=vehicle)
    orders = FleetOrder.objects.filter(filter_request)
    bolt_income = orders.aggregate(total_price=Coalesce(Sum('price'), 0),
                                   total_tips=Coalesce(Sum('tips'), 0),
                                   total_count=Count('id'))
    total_bolt_income = Decimal(bolt_income['total_price'] * 0.75004 +
                                bolt_income['total_tips'])
    return total_bolt_income, orders, bolt_income


def get_vehicle_income(driver, start, end, spending_rate, rent):
    vehicle_income = {}
    start_week = start
    end_week = end
    bolt_weekly = WeeklyReport.objects.filter(report_from=start, report_to=end,
                                              driver=driver, fleet__name="Bolt").aggregate(
        bonuses=Coalesce(Sum('bonuses'), 0, output_field=DecimalField()),
        kasa=Coalesce(Sum('total_amount_without_fee'), 0, output_field=DecimalField()),
        compensations=Coalesce(Sum('compensations'), 0, output_field=DecimalField()),
    )
    driver_rent = RentInformation.objects.filter(
        driver=driver, report_from__range=(start, end)).aggregate(
        distance=Coalesce(Sum('rent_distance'), Decimal(0)))['distance']
    while start <= end:
        start_time = timezone.make_aware(datetime.combine(start, time.min))
        end_time = timezone.make_aware(datetime.combine(start, time.max))
        daily_income = calculate_income_partner(driver, start_time, end_time, spending_rate, rent, driver_rent)
        for vehicle, income in daily_income.items():
            if not vehicle_income.get(vehicle):
                vehicle_income[vehicle] = income
            else:
                vehicle_income[vehicle] += income
        start += timedelta(days=1)
    driver_bonus = {}
    weekly_reshuffles = check_reshuffle(driver, start_week, end_week)
    for shift in weekly_reshuffles:
        if bolt_weekly['bonuses']:
            shift_bolt_kasa = calculate_bolt_kasa(driver, shift.swap_time,
                                                  shift.end_time, vehicle=shift.swap_vehicle)[0]
            reshuffle_bonus = shift_bolt_kasa / Decimal(
                (bolt_weekly['kasa'] - bolt_weekly['compensations'] - bolt_weekly['bonuses'])) * bolt_weekly['bonuses']
            if not driver_bonus.get(shift.swap_vehicle.pk):
                driver_bonus[shift.swap_vehicle.pk] = reshuffle_bonus
            else:
                driver_bonus[shift.swap_vehicle.pk] += reshuffle_bonus
    for car, bonus in driver_bonus.items():
        if not vehicle_income.get(car):
            vehicle_income[car] = bonus * spending_rate
        else:
            vehicle_income[car] += bonus * spending_rate

    return vehicle_income


def calculate_income_partner(driver, start, end, spending_rate, rent, driver_rent=None):
    vehicle_income = {}
    if driver_rent is None:
        driver_rent = RentInformation.objects.filter(
            driver=driver, report_from=start).aggregate(
            distance=Coalesce(Sum('rent_distance'), Decimal(0)))['distance']
    reshuffles = check_reshuffle(driver, start, end)
    rent_vehicle = VehicleRent.objects.filter(driver=driver,
                                              report_from__range=(start, end)).values('vehicle').annotate(
        vehicle_distance=Coalesce(Sum('rent_distance'), Decimal(0)))
    for reshuffle in reshuffles:
        total_gross_kasa = 0
        start_period, end_period = find_reshuffle_period(reshuffle, start, end)
        vehicle = reshuffle.swap_vehicle.pk
        fleets = Fleet.objects.filter(fleetsdriversvehiclesrate__driver=driver, deleted_at=None).exclude(
            name="Ninja").distinct()
        for fleet in fleets:
            if isinstance(fleet, BoltRequest):
                total_gross_kasa += calculate_bolt_kasa(driver, start_period, end_period, vehicle=vehicle)[0]
            else:
                total_gross_kasa += Decimal(fleet.get_earnings_per_driver(driver, start_period, end_period)[0])
        total_kasa = Decimal(total_gross_kasa) * spending_rate

        if not vehicle_income.get(vehicle):
            vehicle_income[vehicle] = total_kasa
        else:
            vehicle_income[vehicle] += total_kasa
    for pay_rent in rent_vehicle:
        vehicle = pay_rent['vehicle']
        total_rent = pay_rent['vehicle_distance'] / driver_rent * rent if driver_rent else 0
        vehicle_income[vehicle] += total_rent
    payment = Payments.objects.filter(report_from__range=(start, end), driver=driver, fleet__name="Bolt")
    compensations = payment.aggregate(
        compensations=Coalesce(Sum('compensations'), 0, output_field=DecimalField()))['compensations']
    if compensations:
        vehicles = len(vehicle_income.values())
        for key in vehicle_income:
            vehicle_income[key] += compensations / vehicles * spending_rate
    return vehicle_income


def get_failed_income(payment):
    vehicle_income = {}
    start = timezone.localtime(payment.report_from)
    end = timezone.localtime(payment.report_to)
    bolt_fleet = Fleet.objects.get(name="Bolt", partner=payment.partner)
    driver_kasa = 0
    driver_reshuffles = check_reshuffle(payment.driver, start, end)

    while start.date() <= end.date():
        if start.date() < end.date():
            start_report = start
            end_report = timezone.make_aware(datetime.combine(start, time.max.replace(microsecond=0)))
        else:
            start_report = timezone.make_aware(datetime.combine(start, time.min))
            end_report = end

        bolt_day_cash = CustomReport.objects.filter(
            report_to__lte=end_report, report_from__gte=start_report,
            fleet=bolt_fleet, driver=payment.driver).aggregate(
            total_amount_cash=Coalesce(Sum('total_amount_cash'), Decimal(0)))['total_amount_cash']

        reshuffles = check_reshuffle(payment.driver, start_report, end_report)
        orders_total_cash = 0
        cash_discount = 0
        for reshuffle in reshuffles:
            total_kasa = 0
            total_cash = 0
            start_period, end_period = find_reshuffle_period(reshuffle, start_report, end_report)
            vehicle = reshuffle.swap_vehicle.pk
            fleets = Fleet.objects.filter(fleetsdriversvehiclesrate__driver=payment.driver, deleted_at=None).exclude(
                name="Ninja").distinct()
            for fleet in fleets:
                if isinstance(fleet, BoltRequest):
                    kasa, bolt_orders = calculate_bolt_kasa(payment.driver, start_period, end_period, vehicle)[:2]
                    bolt_cash = bolt_orders.filter(payment=PaymentTypes.CASH).aggregate(
                        total_price=Coalesce(Sum('price'), 0),
                        total_tips=Coalesce(Sum('tips'), 0))
                    cash = Decimal(bolt_cash['total_price'] + bolt_cash['total_tips'])
                    orders_total_cash += cash
                else:
                    kasa, cash = fleet.get_earnings_per_driver(payment.driver, start_period, end_period)
                total_kasa += Decimal(kasa)
                total_cash += Decimal(cash)
                print(f"kasa {total_kasa}, cash {total_cash} ")
            driver_kasa += total_kasa
            print(driver_kasa)
            total_income = total_kasa - total_cash
            if not vehicle_income.get(vehicle):
                vehicle_income[vehicle] = total_income
            else:
                vehicle_income[vehicle] += total_income
        if orders_total_cash != bolt_day_cash and reshuffles:
            quantity_reshuffles = reshuffles.values_list('swap_vehicle').distinct().count()
            cash_discount += orders_total_cash - bolt_day_cash
            print(f"discount {cash_discount}")
            vehicle_card_bonus = Decimal(cash_discount / quantity_reshuffles)
            for key, value in vehicle_income.items():
                vehicle_income[key] += vehicle_card_bonus
        start += timedelta(days=1)
    if driver_kasa < payment.kasa and driver_reshuffles:
        quantity = driver_reshuffles.values_list('swap_vehicle').distinct().count()
        cash_discount = payment.kasa - driver_kasa
        vehicle_card_bonus = Decimal(cash_discount / quantity)
        for key, value in vehicle_income.items():
            vehicle_income[key] += vehicle_card_bonus
    return vehicle_income


def get_today_statistic(start, end, driver):
    kasa = 0
    card = 0
    fleets = Fleet.objects.filter(fleetsdriversvehiclesrate__driver=driver, deleted_at=None).exclude(
        name="Ninja").distinct()
    orders = FleetOrder.objects.filter(accepted_time__gt=start,
                                       state=FleetOrder.COMPLETED,
                                       driver=driver).order_by('-finish_time')
    accepted_times = None
    if orders:
        accepted_times = timezone.localtime(orders.last().accepted_time).time().strftime('%H:%M')

    mileage = orders.aggregate(order_mileage=Coalesce(Sum('distance'), Decimal(0)))['order_mileage']
    canceled_orders = FleetOrder.objects.filter(accepted_time__gt=start,
                                                state=FleetOrder.DRIVER_CANCEL,
                                                driver=driver).count()
    fleet_list = []
    for fleet in fleets:
        fleet_orders = orders.filter(fleet=fleet.name)
        if isinstance(fleet, BoltRequest):
            fleet_cash = fleet_orders.filter(payment=PaymentTypes.CASH).aggregate(
                cash_kasa=Coalesce(Sum('price'), Value(0)))['cash_kasa']
            fleet_kasa = (1 - fleet.fees) * fleet_orders.aggregate(kasa=Coalesce(Sum('price'), Value(0)))['kasa']
        else:
            fleet_kasa, fleet_cash = fleet.get_earnings_per_driver(driver, start, end)

        fleet_mileage = fleet_orders.aggregate(order_mileage=Coalesce(Sum('distance'), Decimal(0)))['order_mileage']
        road_time = fleet_orders.aggregate(order_time=Coalesce(Sum('road_time'), timedelta()))['order_time']
        fleet_orders_rejected = FleetOrder.objects.filter(accepted_time__gt=start,
                                                          state=FleetOrder.DRIVER_CANCEL,
                                                          driver=driver, fleet=fleet.name).count()
        fleet_orders_accepted = fleet_orders.count()
        card += Decimal(fleet_kasa - fleet_cash)
        kasa += Decimal(fleet_kasa)
        if fleet_kasa:
            fleet_list.append({
                "fleet": fleet,
                "report_from": start,
                "report_to": end,
                "total_kasa": fleet_kasa,
                "total_orders_rejected": fleet_orders_rejected,
                "total_orders_accepted": fleet_orders_accepted,
                "mileage": fleet_mileage,
                "efficiency": round(Decimal(fleet_kasa) / fleet_mileage, 2) if fleet_mileage else 0,
                "road_time": road_time,
                "driver": driver,
                "partner": driver.partner,
            })

    return kasa, card, mileage, orders.count(), canceled_orders, accepted_times, fleet_list


def send_notify_to_check_car(wrong_cars, partner_pk):
    text = ""
    for driver, car in wrong_cars.items():
        driver_name = Driver.objects.filter(pk=int(driver)).annotate(
            full_name=Func(F('name'), Value(' '), F('second_name'), function='CONCAT')
        ).values('full_name').first()
        ignore = ParkSettings.get_value("IGNORE_DRIVER", partner=partner_pk)
        if ignore == driver_name['full_name']:
            continue
        text += f"{driver_name['full_name']} працює на {car}\n"
    if text:
        text += "Перевірте, будь ласка, зміни водіїв"
        managers_chat_id = list(
            Manager.objects.filter(managers_partner=partner_pk, chat_id__isnull=False).exclude(
                chat_id='').values_list('chat_id', flat=True))
        managers_chat_id.append(ParkSettings.get_value("DEVELOPER_CHAT_ID"))
        for chat_id in managers_chat_id:
            send_long_message(chat_id, text)
