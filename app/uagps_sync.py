import json
from datetime import datetime, timedelta, time

import requests
from _decimal import Decimal
from django.utils import timezone

from app.models import (Driver, GPSNumber, RentInformation, FleetOrder, CredentialPartner, ParkSettings, Fleet,
                        Partner, VehicleRent, Vehicle, DriverReshuffle)
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
            print(response.json())
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
            print(result_list)
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
            order_params, previous_finish_time = self.get_order_parameters(completed, end_report, reshuffle.swap_vehicle)

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

    def get_road_distance(self, start, end, schema_drivers=None):
        road_dict = {}
        if not schema_drivers:
            schema_drivers = DriverReshuffle.objects.filter(
                partner=self.partner, swap_time__date=timezone.localtime()).values_list(
                'driver_start', flat=True)
        drivers = Driver.objects.filter(pk__in=schema_drivers)
        for driver in drivers:
            if RentInformation.objects.filter(report_from__date=start, driver=driver) and len(drivers) != 1:
                continue
            road_dict[driver] = self.get_driver_rent(start, end, driver)
            print(road_dict)
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

    def get_order_parameters(self, orders, end, vehicle):
        parameters = []
        previous_finish_time = None
        for order in orders:
            end_report = order.finish_time if order.finish_time < end else end
            if previous_finish_time is None or order.accepted_time >= previous_finish_time:
                report = self.get_params_for_report(self.get_timestamp(timezone.localtime(order.accepted_time)),
                                                    self.get_timestamp(timezone.localtime(end_report)),
                                                    vehicle.gps.gps_id)
                previous_finish_time = end_report
            elif order.finish_time <= previous_finish_time:
                continue
            else:
                report = self.get_params_for_report(self.get_timestamp(timezone.localtime(previous_finish_time)),
                                                    self.get_timestamp(timezone.localtime(end_report)),
                                                    vehicle.gps.gps_id)
            parameters.append(report)
        return parameters, previous_finish_time

    def get_vehicle_rent(self, start, end, driver):
        no_vehicle_gps = []
        parameters = []
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
                if reshuffle.swap_vehicle.gps:
                    road_distance = 0
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
        reshuffles = check_reshuffle(driver, start, end)
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

    def calculate_driver_vehicle_rent(self, start, end, driver, result):
        distance, road_time = result[0], result[1]
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

    def save_daily_rent(self, start, end, drivers):
        if not redis_instance().exists(f"{self.partner.id}_remove_gps"):
            in_road = self.get_road_distance(start, end, drivers)
            no_vehicle_gps = []
            for driver, result in in_road.items():
                no_gps_list = self.calculate_driver_vehicle_rent(start, end, driver, result)
                no_vehicle_gps.extend(no_gps_list)
            if no_vehicle_gps:
                result_string = ', '.join([str(obj) for obj in set(no_vehicle_gps)])
                bot.send_message(chat_id=ParkSettings.get_value("DEVELOPER_CHAT_ID"),
                                 text=f"У авто {result_string} відсутній gps")

    def check_today_rent(self):
        if not redis_instance().exists(f"{self.partner.id}_remove_gps"):
            start = timezone.make_aware(datetime.combine(timezone.localtime(), time.min))
            end = timezone.make_aware(datetime.combine(timezone.localtime(), time.max))
            in_road = self.get_road_distance(start, end)
            text = "Поточна статистика\n"
            for driver, result in in_road.items():
                distance, road_time, end_time = result
                total_km = 0
                if not end_time:
                    end_time = timezone.localtime()
                reshuffles = check_reshuffle(driver, start, end, gps=True)
                for reshuffle in reshuffles:
                    if reshuffle.end_time < end_time:
                        total_km += self.total_per_day(reshuffle.swap_vehicle.gps.gps_id,
                                                       reshuffle.swap_time,
                                                       reshuffle.end_time)
                    elif reshuffle.swap_time < end_time:
                        total_km += self.total_per_day(reshuffle.swap_vehicle.gps.gps_id,
                                                       reshuffle.swap_time,
                                                       end_time)
                    else:
                        continue
                rent_distance = total_km - distance
                driver_obj = Driver.objects.get(id=driver)
                kasa, card, mileage, orders, canceled_orders = get_today_statistic(start, end_time, driver_obj)
                time_now = timezone.localtime(end_time)
                if kasa and mileage:
                    text += f"Водій: {driver_obj} час {time_now.strftime('%H:%M')} \n"\
                            f"Каса: {round(kasa, 2)}\n"\
                            f"Виконано замовлень: {orders}\n"\
                            f"Скасовано замовлень: {canceled_orders}\n"\
                            f"Пробіг під замовленням: {mileage}\n"\
                            f"Ефективність: {round(kasa / mileage, 2)}\n"\
                            f"Холостий пробіг: {rent_distance}\n\n"
                else:
                    text += f"Водій {driver_obj} ще не виконав замовлень\n" \
                            f"Холостий пробіг: {rent_distance}\n\n"
            if timezone.localtime().time() > time(7, 0):
                send_long_message(chat_id=ParkSettings.get_value("DEVELOPER_CHAT_ID"), text=text)

