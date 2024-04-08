import json
from datetime import datetime, timedelta, time

import requests
from _decimal import Decimal

from django.db.models import Q
from django.utils import timezone
from telegram import ParseMode

from app.models import (Driver, GPSNumber, RentInformation, FleetOrder, CredentialPartner, ParkSettings, Fleet,
                        Partner, VehicleRent, Vehicle, DriverReshuffle, DriverPayments)
from auto_bot.handlers.driver_manager.utils import get_today_statistic, find_reshuffle_period
from auto_bot.handlers.order.utils import check_reshuffle
from auto_bot.main import bot
from auto_bot.utils import send_long_message
from scripts.redis_conn import redis_instance, get_logger
from selenium_ninja.synchronizer import AuthenticationError


class UaGpsSynchronizer(Fleet):
    @staticmethod
    def create_session(*args):
        partner_obj = Partner.objects.get(pk=args[0])
        params = {
            'svc': 'token/login',
            'params': json.dumps({"token": args[1]})
        }
        response = requests.get(f"{partner_obj.gps_url}wialon/ajax.html", params=params)
        if response.json().get("error"):
            raise AuthenticationError(f"gps token incorrect.")
        # token = SeleniumTools(partner).create_gps_session(login, password, partner_obj.gps_url)
        return args[1]

    def get_base_url(self):
        return self.partner.gps_url

    def get_session(self):
        if not redis_instance().exists(f"{self.partner.id}_gps_session"):

            params = {
                'svc': 'token/login',
                'params': json.dumps({"token": CredentialPartner.get_value('UAGPS_TOKEN', partner=self.partner)})
            }
            response = requests.get(f"{self.get_base_url()}wialon/ajax.html", params=params)
            if response.json().get("error"):
                print(response.json())
                # if not redis_instance().exists(f"{self.partner.id}_remove_gps"):
                #     redis_instance().set(f"{self.partner.id}_remove_gps", response.json().get("error"), ex=86400)
                return
            # redis_instance().delete(f"{self.partner.id}_remove_gps")
            redis_instance().set(f"{self.partner.id}_gps_session", response.json()['eid'], ex=240)
        return redis_instance().get(f"{self.partner.id}_gps_session")

    def get_gps_id(self):
        if not redis_instance().exists(f"{self.partner.id}_gps_id"):
            payload = {"spec": {"itemsType": "avl_resource", "propName": "sys_name",
                                "propValueMask": "*", "sortType": ""},
                       "force": 1, "flags": 5, "from": 0, "to": 4294967295}
            params = {
                'sid': self.get_session(),
                'svc': 'core/search_items',
            }
            params.update({'params': json.dumps(payload)})
            response = requests.post(f"{self.get_base_url()}wialon/ajax.html", params=params)
            gps_id = response.json()['items'][0]['id'] if len(response.json()['items']) == 1 else \
                response.json()['items'][1]['id']
            redis_instance().set(f"{self.partner.id}_gps_id", gps_id)
        return redis_instance().get(f"{self.partner.id}_gps_id")

    def synchronize(self):
        if not redis_instance().exists(f"{self.partner.id}_remove_gps"):
            params = {
                'sid': self.get_session(),
                'svc': 'core/update_data_flags',
                'params': json.dumps({"spec": [{"type": "type",
                                                "data": "avl_unit",
                                                "flags": 1,
                                                "mode": 0}]})
            }
            response = requests.get(f"{self.get_base_url()}wialon/ajax.html", params=params)
            for vehicle in response.json():
                data = {"name": vehicle['d']['nm'],
                        "partner": self.partner}
                obj, created = GPSNumber.objects.get_or_create(gps_id=vehicle['i'],
                                                               defaults=data)
                if not created:
                    for key, value in data.items():
                        setattr(obj, key, value)
                    obj.save()
                for partner_vehicle in Vehicle.objects.filter(partner=self.partner, gps__isnull=True):
                    licence_number = ''.join(char for char in partner_vehicle.licence_plate if char.isdigit())
                    if licence_number in vehicle['d']['nm']:
                        partner_vehicle.gps = obj
                        partner_vehicle.save()
                        break

    def get_params_for_report(self, start_time, end_time, vehicle_id, sid=None):
        parameters = {
            "reportResourceId": self.get_gps_id(),
            "reportObjectId": vehicle_id,
            "reportObjectSecId": 0,
            "reportTemplateId": 1,
            "reportTemplate": None,
            "interval": {
                "from": start_time,
                "to": end_time,
                "flags": 16777216
            }
        }
        params = {
            "svc": "report/exec_report",
            "params": parameters
        }
        if sid:
            params['sid'] = sid
            params['params'] = json.dumps(parameters)
        return params

    def generate_report(self, params, orders=False):
        report = requests.get(f"{self.get_base_url()}wialon/ajax.html", params=params)
        items = report.json() if isinstance(report.json(), list) else [report.json()]
        result_list = []
        for item in items:
            try:
                raw_time = item['reportResult']['stats'][4][1]
                clean_time = [int(i) for i in raw_time.split(':')]
                raw_distance = item['reportResult']['stats'][5][1]
            except ValueError:
                raw_time = item['reportResult']['stats'][12][1]
                clean_time = [int(i) for i in raw_time.split(':')]
                raw_distance = item['reportResult']['stats'][11][1]

            except KeyError:
                bot.send_message(chat_id=ParkSettings.get_value("DEVELOPER_CHAT_ID"), text=f"{item}")
            result_list.append((Decimal(raw_distance.split(' ')[0]), timedelta(hours=clean_time[0],
                                                                               minutes=clean_time[1],
                                                                               seconds=clean_time[2])))
        if orders:
            return result_list
        else:
            road_distance = sum(item[0] for item in result_list)
            road_time = sum((result[1] for result in result_list), timedelta())
            return road_distance, road_time

    def generate_batch_report(self, parameters, orders=False):
        params = {
            "svc": "core/batch",
            "sid": self.get_session(),
            "params": json.dumps(parameters)
        }
        return self.generate_report(params, orders)

    @staticmethod
    def get_timestamp(timeframe):
        return int(timeframe.timestamp())

    def get_driver_rent(self, start, end, driver):
        parameters = []
        total_distance = 0
        total_time = timedelta()
        previous_finish_time = None
        reshuffles = check_reshuffle(driver, start, end, gps=True)
        for reshuffle in reshuffles:
            start_report, end_report = find_reshuffle_period(reshuffle, start, end)
            completed = FleetOrder.objects.filter(driver=driver,
                                                  state=FleetOrder.COMPLETED,
                                                  accepted_time__gte=start_report,
                                                  accepted_time__lt=end_report).order_by('accepted_time')
            order_params, previous_finish_time = self.get_order_parameters(completed, end_report,
                                                                           reshuffle.swap_vehicle)

            parameters.extend(order_params)
            if (timezone.localtime(start_report).time() == time.min or
                    (driver.schema and start_report.time() == driver.schema.shift_time)):
                yesterday_order = FleetOrder.objects.filter(driver=driver,
                                                            finish_time__gt=start_report,
                                                            state=FleetOrder.COMPLETED,
                                                            accepted_time__lte=start_report).first()
                if yesterday_order and yesterday_order.vehicle.gps:
                    try:
                        report = self.get_params_for_report(self.get_timestamp(start_report),
                                                            self.get_timestamp(timezone.localtime(
                                                                yesterday_order.finish_time)),
                                                            reshuffle.swap_vehicle.gps.gps_id)
                        parameters.append(report)
                    except AttributeError as e:
                        get_logger().error(e)
                        continue
        batch_size = 25
        batches = [parameters[i:i + batch_size] for i in range(0, len(parameters), batch_size)]
        for batch in batches:
            distance, road_time = self.generate_batch_report(batch)
            total_distance += distance
            total_time += road_time
        return total_distance, total_time, previous_finish_time

    def get_road_distance(self, start, end, schema_drivers=None, payment=None):
        road_dict = {}
        if not schema_drivers:
            schema_drivers = DriverReshuffle.objects.filter(
                partner=self.partner, swap_time__range=(start, end),
                driver_start__isnull=False).values_list(
                'driver_start', flat=True)
        drivers = Driver.objects.filter(pk__in=schema_drivers)
        for driver in drivers:
            if not driver.schema.is_weekly() and not payment:
                last_payment = DriverPayments.objects.filter(
                    driver=driver,
                    report_to__date=start).order_by("-report_from").last()
                if last_payment and last_payment.report_to > start:
                    start = timezone.localtime(last_payment.report_to)
            if RentInformation.objects.filter(report_from__date=start, driver=driver) and len(drivers) != 1:
                continue
            road_dict[driver] = self.get_driver_rent(start, end, driver)
        return road_dict

    def get_order_distance(self, orders):
        batch_params = []
        updated_orders = []
        for instance in orders:
            batch_params.append(self.get_params_for_report(self.get_timestamp(instance.accepted_time),
                                                           self.get_timestamp(instance.finish_time),
                                                           instance.vehicle.gps.gps_id))
        if batch_params:
            batch_size = 50
            batches = [batch_params[i:i + batch_size] for i in range(0, len(batch_params), batch_size)]

            distance_list = []

            for batch in batches:
                distance_list.extend(self.generate_batch_report(batch, True))
            for order, (distance, road_time) in zip(orders, distance_list):
                order.distance = distance
                order.road_time = road_time
                updated_orders.append(order)
            FleetOrder.objects.bulk_update(updated_orders, fields=['distance', 'road_time'], batch_size=200)

    def get_non_order_message(self, start_time, end_time, driver_pk):
        message = ''
        reshuffles = check_reshuffle(driver_pk, start_time, end_time, gps=True)
        prev_order_end_time = start_time

        for reshuffle in reshuffles:
            empty_time_slots = []
            parameters = []
            if timezone.localtime(reshuffle.swap_time) > prev_order_end_time + timedelta(minutes=1):
                empty_time_slots.append((prev_order_end_time, timezone.localtime(reshuffle.swap_time)))

            start, end = find_reshuffle_period(reshuffle, start_time, end_time)

            prev_order_end_time = start
            orders = FleetOrder.objects.filter(Q(driver=driver_pk,
                                                 state=FleetOrder.COMPLETED) &
                                               Q(Q(accepted_time__range=(start, end)) |
                                                 Q(accepted_time__lt=start,
                                                   finish_time__gt=start))).order_by('accepted_time')

            if orders.exists():
                for order in orders:
                    if prev_order_end_time < order.accepted_time:
                        empty_time_slots.append((prev_order_end_time, timezone.localtime(order.accepted_time)))
                    prev_order_end_time = timezone.localtime(order.finish_time)
                if prev_order_end_time < end:
                    empty_time_slots.append((prev_order_end_time, end))
            else:
                empty_time_slots.append((start, end))
            prev_order_end_time = end
            for slot in empty_time_slots:
                parameters.append(self.get_params_for_report(self.get_timestamp(slot[0]),
                                                             self.get_timestamp(slot[1]),
                                                             reshuffle.swap_vehicle.gps.gps_id))
            result = self.generate_batch_report(parameters, True)
            results_with_slots = list(zip(empty_time_slots, result))
            for slot, result in results_with_slots:
                if result[0]:
                    message += f"Час: {slot[0].strftime('%H:%M')} - {slot[1].strftime('%H:%M')} Холостий пробіг: {result[0]}\n"
        return message

    def get_order_parameters(self, orders, end, vehicle):
        parameters = []
        previous_finish_time = None
        for order in orders:
            end_report = order.finish_time if order.finish_time < end else end
            if previous_finish_time is None or order.accepted_time >= previous_finish_time:
                report = self.get_params_for_report(self.get_timestamp(timezone.localtime(order.accepted_time)),
                                                    self.get_timestamp(timezone.localtime(end_report)),
                                                    vehicle.gps.gps_id)
            elif order.finish_time <= previous_finish_time:
                continue
            else:
                report = self.get_params_for_report(self.get_timestamp(timezone.localtime(previous_finish_time)),
                                                    self.get_timestamp(timezone.localtime(end_report)),
                                                    vehicle.gps.gps_id)
            previous_finish_time = end_report
            parameters.append(report)
        return parameters, previous_finish_time

    def get_vehicle_rent(self, start, end, driver):
        no_vehicle_gps = []

        reshuffles = check_reshuffle(driver, start, end)
        unique_vehicle_count = reshuffles.values('swap_vehicle').distinct().count()
        if unique_vehicle_count == 1:
            rent_distance = RentInformation.objects.filter(report_from=start,
                                                           report_to=end,
                                                           driver=driver).first().rent_distance
            data = {"report_from": start,
                    "report_to": end,
                    "rent_distance": rent_distance,
                    "vehicle": reshuffles.first().swap_vehicle,
                    "partner": self.partner}
            VehicleRent.objects.get_or_create(report_from__date=start,
                                              report_to=end,
                                              vehicle=reshuffles.first().swap_vehicle,
                                              driver=driver,
                                              defaults=data)
        else:

            for reshuffle in reshuffles:
                road_distance = 0
                parameters = []
                if reshuffle.swap_vehicle.gps:
                    start_period, end_period = find_reshuffle_period(reshuffle, start, end)
                    orders = FleetOrder.objects.filter(
                        driver=driver,
                        state=FleetOrder.COMPLETED,
                        accepted_time__range=(start_period, end_period)).order_by('accepted_time')
                    parameters.extend(self.get_order_parameters(orders, end, reshuffle.swap_vehicle)[0])
                    batch_size = 40
                    batches = [parameters[i:i + batch_size] for i in range(0, len(parameters), batch_size)]
                    for batch in batches:
                        road_distance += self.generate_batch_report(batch)[0]
                    total_km = self.total_per_day(reshuffle.swap_vehicle.gps.gps_id, start_period, end_period)
                    rent_distance = total_km - road_distance
                    data = {"report_from": start_period,
                            "report_to": end_period,
                            "rent_distance": rent_distance,
                            "vehicle": reshuffle.swap_vehicle,
                            "partner": self.partner}
                    VehicleRent.objects.get_or_create(report_from=start_period,
                                                      report_to=end_period,
                                                      vehicle=reshuffle.swap_vehicle,
                                                      driver=driver,
                                                      defaults=data)
                else:
                    if reshuffle.swap_vehicle not in no_vehicle_gps:
                        no_vehicle_gps.append(reshuffle.swap_vehicle)
                    continue
        return no_vehicle_gps

    def total_per_day(self, gps_id, start, end):
        distance = self.generate_report(self.get_params_for_report(self.get_timestamp(start),
                                                                   self.get_timestamp(end),
                                                                   gps_id,
                                                                   self.get_session()))[0]
        return distance

    def calc_total_km(self, driver, start, end):
        driver_vehicles = []
        total_km = 0
        reshuffles = check_reshuffle(driver, start, end, gps=True)
        for reshuffle in reshuffles:
            driver_vehicles.append(reshuffle.swap_vehicle)
            start_report, end_report = find_reshuffle_period(reshuffle, start, end)
            try:
                total_km += self.total_per_day(reshuffle.swap_vehicle.gps.gps_id,
                                               start_report,
                                               end_report)
            except AttributeError as e:
                get_logger().error(e)
                continue
        return total_km, driver_vehicles

    def calculate_driver_vehicle_rent(self, start, end, driver, result, payment=None):
        distance, road_time = result[0], result[1]
        if not payment and not driver.schema.is_weekly():
            last_payment = DriverPayments.objects.filter(
                driver=driver,
                report_to__date=start).order_by("-report_from").last()
            if last_payment and last_payment.report_to > start:
                start = timezone.localtime(last_payment.report_to)
        total_km = self.calc_total_km(driver, start, end)[0]
        rent_distance = total_km - distance
        data = {
            "report_from": start,
            "report_to": end,
            "driver": driver,
            "partner": self.partner,
            "rent_distance": rent_distance
        }
        driver_rent, created = RentInformation.objects.get_or_create(
            report_from__date=start,
            driver=driver,
            partner=self.partner,
            defaults=data)
        if not created:
            for key, value in data.items():
                setattr(driver_rent, key, value)
            driver_rent.save()
            VehicleRent.objects.filter(report_from__range=(start, end),
                                       driver=driver, partner=self.partner).delete()
        no_gps_list = self.get_vehicle_rent(start, end, driver)
        return no_gps_list

    def save_daily_rent(self, start, end, drivers, payment):
        if not redis_instance().exists(f"{self.partner.id}_remove_gps"):
            in_road = self.get_road_distance(start, end, drivers, payment=payment)
            no_vehicle_gps = []
            for driver, result in in_road.items():
                no_gps_list = self.calculate_driver_vehicle_rent(start, end, driver, result, payment=payment)
                no_vehicle_gps.extend(no_gps_list)
            if no_vehicle_gps:
                result_string = ', '.join([str(obj) for obj in set(no_vehicle_gps)])
                bot.send_message(chat_id=ParkSettings.get_value("DEVELOPER_CHAT_ID"),
                                 text=f"У авто {result_string} відсутній gps")

    @staticmethod
    def generate_text_message(
            driver, kasa, distance, orders, canceled_orders, accepted_times, rent_distance, road_time, end_time,
            start_reshuffle):
        time_now = timezone.localtime(end_time)
        if kasa and distance:
            return f"<b>{driver}</b> \n" \
                   f"<u>Звіт з {start_reshuffle} по {time_now.strftime('%H:%M')}</u> \n\n" \
                   f"Початок роботи: {accepted_times}\n" \
                   f"Каса: {round(kasa, 2)}\n" \
                   f"Виконано замовлень: {orders}\n" \
                   f"Скасовано замовлень: {canceled_orders}\n" \
                   f"Пробіг під замовленням: {distance}\n" \
                   f"Ефективність: {round(kasa / (distance + rent_distance), 2)}\n" \
                   f"Холостий пробіг: {rent_distance}\n" \
                   f"Час у дорозі: {road_time}\n\n"
        else:
            return f"Водій {driver} ще не виконав замовлень\n" \
                   f"Холостий пробіг: {rent_distance}\n\n"

    def process_driver_data(self, driver, result, start, end, chat_id, start_reshuffle=None):
        distance, road_time, end_time = result
        end_time = end_time or timezone.localtime()
        total_km = self.calc_total_km(driver, start, end_time)[0]
        rent_distance = total_km - distance
        kasa, card, mileage, orders, canceled_orders, accepted_times = get_today_statistic(start, end_time, driver)
        text = self.generate_text_message(driver, kasa, distance, orders, canceled_orders, accepted_times,
                                          rent_distance, road_time, end_time, start_reshuffle)
        # if timezone.localtime().time() > time(7, 0):
        #     send_long_message(chat_id=chat_id, text=text)
        return text

    def check_today_rent(self):
        if not redis_instance().exists(f"{self.partner.id}_remove_gps"):
            start = timezone.make_aware(datetime.combine(timezone.localtime(), time.min))
            end = timezone.make_aware(datetime.combine(timezone.localtime(), time.max))
            in_road = self.get_road_distance(start, end)
            text = "Поточна статистика\n"
            for driver, result in in_road.items():
                reshuffles = DriverReshuffle.objects.filter(driver_start=driver,
                                                            swap_time__date=timezone.localtime()).order_by('swap_time')
                start_reshuffle = timezone.localtime(reshuffles.earliest('swap_time').swap_time)
                text += self.process_driver_data(
                    driver, result, start, end, driver.chat_id, start_reshuffle.strftime("%H:%M"))
            if timezone.localtime().time() > time(7, 0):
                send_long_message(
                    chat_id=ParkSettings.get_value("DRIVERS_CHAT", partner=self.partner),
                    text=text
                )
