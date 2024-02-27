from collections import defaultdict
from datetime import datetime, timedelta, time

from _decimal import Decimal
from django.db.models import Sum, Avg, DecimalField, ExpressionWrapper, F, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from app.bolt_sync import BoltRequest
from app.models import CarEfficiency, Driver, SummaryReport, \
    Vehicle, RentInformation, DriverEfficiency, DriverSchemaRate, SalaryCalculation, \
    DriverPayments, FleetOrder, VehicleRent, Schema, Fleet, CustomUser, CustomReport, PaymentTypes, Payments
from auto_bot.handlers.order.utils import check_reshuffle


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
        shift_time = time.max
        date = datetime.strptime(day, "%Y-%m-%d") - timedelta(days=1) if day else timezone.localtime() - timedelta(days=1)
        yesterday = date
    start = timezone.make_aware(datetime.combine(date, time.min))
    previous_end = timezone.make_aware(datetime.combine(yesterday, time.max))
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
    return start_period, end_period


def create_driver_payments(start, end, driver, schema, driver_report=None, delete=None):
    if not driver_report:
        driver_report = SummaryReport.objects.filter(report_from__range=(start, end),
                                                     driver=driver).aggregate(
            cash=Coalesce(Sum('total_amount_cash'), 0, output_field=DecimalField()),
            kasa=Coalesce(Sum('total_amount_without_fee'), 0, output_field=DecimalField()))
    rent = calculate_rent(start, end, driver)
    rent_value = rent * schema.rent_price
    if delete:
        salary = '%.2f' % (driver_report['kasa'] * schema.rate - driver_report['cash'] - rent_value)
    elif schema.is_dynamic():
        driver_spending = calculate_by_rate(driver, driver_report['kasa'], driver.partner_id)
        salary = '%.2f' % (driver_spending - driver_report['cash'] - rent_value)
    elif schema.is_rent():
        overall_distance = DriverEfficiency.objects.filter(
            report_from__range=(start, end),
            driver=driver).aggregate(
            distance=Coalesce(Sum('mileage'), 0, output_field=DecimalField()))['distance']
        rent = max((overall_distance - schema.limit_distance), 0)
        rent_value = rent * schema.rent_price
        salary = '%.2f' % (driver_report['kasa'] * schema.rate -
                           driver_report['cash'] - schema.rental - rent_value)
    elif schema.is_float():
        rate = get_driver_salary_rate(driver, driver_report['kasa'], driver.partner_id)
        salary = '%.2f' % (driver_report['kasa'] * rate - driver_report['cash'] - rent_value)
    else:
        salary = '%.2f' % (driver_report['kasa'] * schema.rate - driver_report['cash'] - (
            (schema.plan - driver_report['kasa']) * Decimal(1 - schema.rate)
            if driver_report['kasa'] < schema.plan else 0) - rent_value
        )
    data = {"rent_distance": rent,
            "rent_price": schema.rent_price,
            "kasa": driver_report['kasa'],
            "cash": driver_report['cash'],
            "earning": salary,
            "rent": rent_value,
            "payment_type": schema.salary_calculation,
            "partner": schema.partner}
    return data


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
        report_from__range=(start, end_time),
        driver=driver)
    overall_rent = ExpressionWrapper(F('rent_distance') - driver.schema.limit_distance,
                                     output_field=DecimalField())
    total_rent = rent_report.aggregate(distance=Sum(overall_rent))['distance'] or 0
    return total_rent


def calculate_daily_reports(start, end, driver):
    driver_report = SummaryReport.objects.filter(report_from__range=(start, end),
                                                 driver=driver)
    kasa = driver_report.aggregate(kasa=Coalesce(
        Sum('total_amount_without_fee'), 0, output_field=DecimalField()))['kasa'] or 0

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
    drivers = drivers.filter(schema__isnull=False)
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
    for driver in drivers:
        driver_payments_query = DriverPayments.objects.filter(report_from__date=start, report_to__date=end, driver=driver)
        if driver_payments_query.exists():
            payment = driver_payments_query.last()

            if driver.deleted_at in (start, end):
                driver_message = f"{driver} каса: {payment.kasa}\n" \
                                 f"Зарплата {payment.kasa} - Готівка {payment.cash}" \
                                 f" - Холостий пробіг {payment.rent} = {payment.earning}\n"
            else:
                driver_message = message_driver_report(driver, payment)
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


def message_driver_report(driver, payment):
    driver_message = ''
    driver_message += f"{driver} каса: {payment.kasa}\n"
    if payment.rent:
        driver_message += "Холостий пробіг: {0} * {1} = {2}\n".format(
            payment.rent_distance, payment.rent_price, payment.rent)
    if driver.schema.is_rent():
        driver_message += 'Зарплата {0} * {1} - Готівка {2} - Абонплата {3}'.format(
            payment.kasa, driver.schema.rate, payment.cash, driver.schema.rental)
    elif driver.schema.is_dynamic():
        driver_message += 'Зарплата {0} - Готівка {1}'.format(
            payment.earning + payment.cash + payment.rent, payment.cash)
    elif driver.schema.is_float():
        rate = get_driver_salary_rate(driver, payment.kasa, driver.partner.id)
        driver_message += 'Зарплата {0} * {1} - Готівка {2}'.format(
            payment.kasa, rate, payment.cash, payment.rent)
    else:
        driver_message += 'Зарплата {0} * {1} - Готівка {2}'.format(
            payment.kasa, driver.schema.rate, payment.cash)
        if payment.kasa < driver.schema.plan:
            incomplete = (driver.schema.plan - payment.kasa) * Decimal(1 - driver.schema.rate)
            driver_message += " - План {:.2f}".format(incomplete)

    bonuses = payment.get_bonuses()
    penalties = payment.get_penalties()
    driver_message += " + Бонуси: {0} - Штрафи: {1}".format(bonuses, penalties)

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


def get_efficiency(manager_id=None, start=None, end=None):
    yesterday = timezone.localtime().date() - timedelta(days=1)
    if not start and not end:
        if timezone.localtime().weekday():
            start = timezone.localtime().date() - timedelta(days=timezone.localtime().weekday())
        else:
            start = timezone.localtime().date() - timedelta(weeks=1)
        end = yesterday
    effective_vehicle = {}
    report = {}
    vehicles = get_drivers_vehicles_list(manager_id, Vehicle)[0]
    for vehicle in vehicles:
        effect = calculate_efficiency(vehicle, start, end)
        drivers = ", ".join(effect[3])
        if end == yesterday:
            yesterday_effect = calculate_efficiency(vehicle, end, end)
            effective_vehicle[vehicle.licence_plate] = {
                'Водії': drivers,
                'Середня ефективність(грн/км)': effect[0],
                'Ефективність(грн/км)': yesterday_effect[0],
                'КМ всього': effect[1],
                'КМ учора': yesterday_effect[1],
                'Загальна каса': effect[2],
                'Каса вчора': yesterday_effect[2]
            }
        else:
            effective_vehicle[vehicle.licence_plate] = {
                'Водії': drivers,
                'Середня ефективність(грн/км)': effect[0],
                'КМ всього': effect[1],
                'Загальна каса': effect[2]}
    sorted_effective_driver = dict(sorted(effective_vehicle.items(),
                                          key=lambda x: x[1]['Середня ефективність(грн/км)'],
                                          reverse=True))
    for k, v in sorted_effective_driver.items():
        report[k] = [f"{vk}: {vv}\n" for vk, vv in v.items()]
    return report


def calculate_efficiency_driver(driver, start, end):
    efficiency_objects = DriverEfficiency.objects.filter(report_from__range=(start, end), driver=driver)

    unique_vehicles = set()
    driver_vehicles = []

    for obj in efficiency_objects:
        vehicles = obj.vehicles.all().values_list('licence_plate', flat=True)
        unique_vehicles.update(vehicles)

    driver_vehicles.extend(unique_vehicles)

    aggregations = efficiency_objects.aggregate(
        total_kasa=Sum('total_kasa', default=0),
        total_distance=Sum('mileage', default=0),
        total_orders=Sum('total_orders', default=0),
        total_hours=Sum('road_time', default=timedelta()),
        total_orders_rejected=Sum('total_orders_rejected', default=0)
    )

    total_orders = aggregations['total_orders']
    rejected = aggregations['total_orders_rejected']
    completed_orders = total_orders - rejected
    total_distance = aggregations['total_distance']
    total_hours = aggregations['total_hours']

    accept_percent = 100 if rejected == 0 else float('{:.2f}'.format(total_orders/rejected))
    avg_price = 0 if total_orders == 0 else float('{:.2f}'.format(aggregations['total_kasa'] / completed_orders))
    efficiency = 0 if total_distance == 0 else float('{:.2f}'.format(aggregations['total_kasa'] / total_distance))

    total_seconds = int(total_hours.total_seconds()) if total_hours else 0
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    total_hours_formatted = f"{hours:02}:{minutes:02}:{seconds:02}"

    return (efficiency, completed_orders, accept_percent, avg_price, total_distance,
            total_hours_formatted, driver_vehicles)


def get_driver_efficiency_report(manager_id, schema=None, start=None, end=None):
    drivers = get_drivers_vehicles_list(manager_id, Driver)[0]
    yesterday = timezone.localtime().date() - timedelta(days=1)
    if not start and not end:
        if schema:
            report_time = timezone.make_aware(datetime.combine(timezone.localtime().date(), schema.shift_time))
            yesterday = report_time - timedelta(days=1)
            drivers = drivers.filter(schema=schema)
        else:
            report_time = timezone.localtime()
            drivers = drivers.filter(schema__isnull=False)
        end = yesterday
        start = report_time - timedelta(days=report_time.weekday()) if report_time.weekday() else \
            report_time - timedelta(weeks=1)
    else:
        drivers = drivers.filter(schema__isnull=False)
    effective_driver = {}
    report = {}

    for driver in drivers:
        effect = calculate_efficiency_driver(driver, start, end)
        if effect[0]:
            total_kasa, total_rent = calculate_daily_reports(start, end, driver)
            licence_plates = ', '.join(effect[6])
            if end == yesterday:
                yesterday_effect = calculate_efficiency_driver(driver, end, end)
                day_kasa, rent_daily = calculate_daily_reports(end, end, driver)
                efficiency = yesterday_effect[0]
                car_plates = ', '.join(yesterday_effect[6])
                orders = yesterday_effect[1]
                accept_percent = yesterday_effect[2]
                average_price = yesterday_effect[3]
                distance = yesterday_effect[4]
                road_time = yesterday_effect[5]
                effective_driver[driver] = {
                    'Автомобілі': f"{licence_plates} ({car_plates})",
                    'Каса': f"{total_kasa} (+{day_kasa}) грн",
                    'Холостий пробіг': f"{total_rent} (+{rent_daily}) км",
                    'Ефективність': f"{effect[0]} (+{efficiency}) грн/км",
                    'Виконано замовлень': f"{effect[1]} (+{orders})",
                    '% прийнятих': f"{effect[2]} ({accept_percent})",
                    'Cередній чек': f"{effect[3]} ({average_price}) грн",
                    'Пробіг': f"{effect[4]} (+{distance}) км",
                    'Час в дорозі': f"{effect[5]}(+{road_time})"
                }
            else:
                effective_driver[driver] = {
                    'Автомобілі': f"{licence_plates}",
                    'Каса': f"{total_kasa} грн",
                    'Холостий пробіг': f"{total_rent} км",
                    'Ефективність': f"{effect[0]} грн/км",
                    'Виконано замовлень': f"{effect[1]}",
                    '% прийнятих': f"{effect[2]}",
                    'Cередній чек': f"{effect[3]} грн",
                    'Пробіг': f"{effect[4]} км",
                    'Час в дорозі': f"{effect[5]}"
                }
    sorted_effective_driver = dict(sorted(effective_driver.items(),
                                          key=lambda x: float(x[1]['Каса'].split()[0]),
                                          reverse=True))
    for k, v in sorted_effective_driver.items():
        report[k] = [f"{vk}: {vv}\n" for vk, vv in v.items()]
    return report


def get_vehicle_income(driver, start, end, spending_rate, rent):
    vehicle_income = {}
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
    return vehicle_income


def calculate_income_partner(driver, start, end, spending_rate, rent, driver_rent=None):
    vehicle_income = {}
    if driver_rent is None:
        driver_rent = RentInformation.objects.filter(
            driver=driver, report_from=start).aggregate(
            distance=Coalesce(Sum('rent_distance'), Decimal(0)))['distance']
    reshuffles = check_reshuffle(driver, start, end)
    for reshuffle in reshuffles:
        uber_uklon_income = 0
        start_period, end_period = find_reshuffle_period(reshuffle, start, end)
        vehicle = reshuffle.swap_vehicle
        bolt_income = FleetOrder.objects.filter(
            fleet="Bolt",
            accepted_time__range=(start_period, end_period),
            driver=reshuffle.driver_start,
            vehicle=vehicle).aggregate(total_price=Coalesce(Sum('price'), 0),
                                       total_tips=Coalesce(Sum('tips'), 0))
        rent_vehicle = VehicleRent.objects.filter(
            vehicle=vehicle, driver=driver, report_from__range=(start_period, end_period),
            report_to__range=(start_period, end_period)).aggregate(
            vehicle_distance=Coalesce(Sum('rent_distance'), Decimal(0)))['vehicle_distance']

        if driver_rent and rent_vehicle:
            total_rent = rent_vehicle / driver_rent * rent
        else:
            total_rent = 0

        fleets = Fleet.objects.filter(partner=driver.partner, name__in=("Uklon", "Uber"))
        for fleet in fleets:
            uber_uklon_income += Decimal(fleet.get_earnings_per_driver(driver, start_period, end_period)[0])

        total_bolt_income = Decimal(bolt_income['total_price'] * 0.75004 +
                                    bolt_income['total_tips'])
        total_kasa = Decimal((total_bolt_income + uber_uklon_income)) * spending_rate
        total_income = total_kasa + total_rent

        if not vehicle_income.get(vehicle):
            vehicle_income[vehicle] = total_income
        else:
            vehicle_income[vehicle] += total_income
    return vehicle_income


def get_failed_income(payment):
    vehicle_income = {}
    updated_income = {}
    start = timezone.localtime(payment.report_from)
    end = timezone.localtime(payment.report_to)
    bolt_fleet = Fleet.objects.get(name="Bolt", partner=payment.partner)
    while start.date() <= end.date():
        bolt_total_cash = 0
        orders_total_cash = 0
        start_report = start if start < end else timezone.make_aware(datetime.combine(start, time.min))
        end_report = timezone.make_aware(datetime.combine(start, time.max))
        bolt_report = CustomReport.objects.filter(report_to__lte=end_report,
                                                  report_from__gte=start_report,
                                                  fleet=bolt_fleet,
                                                  driver=payment.driver).order_by('report_from').first()
        if bolt_report:
            bolt_total_cash = bolt_report.total_amount_cash
            end_report = bolt_report.report_to
        reshuffles = check_reshuffle(payment.driver, start_report, end_report)
        quantity_reshuffles = reshuffles.count()
        for reshuffle in reshuffles:
            uber_uklon_income = 0
            uber_uklon_cash = 0
            start_period, end_period = find_reshuffle_period(reshuffle, start_report, end_report)
            vehicle = reshuffle.swap_vehicle

            bolt_orders = FleetOrder.objects.filter(
                fleet="Bolt",
                accepted_time__range=(start_period, end_period),
                driver=reshuffle.driver_start,
                vehicle=vehicle)
            bolt_kasa = bolt_orders.aggregate(total_price=Coalesce(Sum('price'), 0),
                                              total_tips=Coalesce(Sum('tips'), 0))
            bolt_cash = bolt_orders.filter(payment=PaymentTypes.CASH).aggregate(total_price=Coalesce(Sum('price'), 0),
                                                                                total_tips=Coalesce(Sum('tips'), 0))
            fleets = Fleet.objects.filter(partner=payment.partner, name__in=("Uklon", "Uber"))
            for fleet in fleets:
                kasa, cash = fleet.get_earnings_per_driver(payment.driver, start_period, end_period)
                uber_uklon_income += Decimal(kasa)
                uber_uklon_cash += Decimal(cash)

            total_bolt_income = Decimal(bolt_kasa['total_price'] * 0.75004 +
                                        bolt_kasa['total_tips'])
            bolt_cash = Decimal(bolt_cash['total_price'] + bolt_cash['total_tips'])
            orders_total_cash += bolt_cash
            total_income = total_bolt_income + uber_uklon_income - uber_uklon_cash - bolt_cash
            if not vehicle_income.get(vehicle):
                vehicle_income[vehicle] = total_income
            else:
                vehicle_income[vehicle] += total_income
        if orders_total_cash != bolt_total_cash and reshuffles:
            cash_discount = orders_total_cash - bolt_total_cash
            vehicle_card_bonus = Decimal(cash_discount / quantity_reshuffles)
            updated_income = {key: value + vehicle_card_bonus for key, value in vehicle_income.items()}
        else:
            updated_income = vehicle_income
        start += timedelta(days=1)
    return updated_income


def get_today_statistic(partner_pk, start, end, driver):
    kasa = 0
    card = 0
    fleets = Fleet.objects.filter(partner=partner_pk, deleted_at=None).exclude(name="Gps")
    orders = FleetOrder.objects.filter(accepted_time__gt=start,
                                       state=FleetOrder.COMPLETED,
                                       driver=driver).order_by('-finish_time')
    canceled_orders = FleetOrder.objects.filter(accepted_time__gt=start,
                                                state=FleetOrder.DRIVER_CANCEL,
                                                driver=driver).count()
    for fleet in fleets:
        if isinstance(fleet, BoltRequest):
            bolt_orders = orders.filter(fleet=fleet.name)
            fleet_cash = bolt_orders.filter(payment=PaymentTypes.CASH).aggregate(
                cash_kasa=Coalesce(Sum('price'), Value(0)))['cash_kasa']
            fleet_kasa = (1 - fleet.fees) * bolt_orders.aggregate(kasa=Coalesce(Sum('price'), Value(0)))['kasa']
        else:
            fleet_kasa, fleet_cash = fleet.get_earnings_per_driver(driver, start, end)
        card += Decimal(fleet_kasa - fleet_cash)
        kasa += Decimal(fleet_kasa)
    mileage = orders.aggregate(order_mileage=Coalesce(Sum('distance'), Decimal(0)))['order_mileage']

    return kasa, card, mileage, orders.count(), canceled_orders
