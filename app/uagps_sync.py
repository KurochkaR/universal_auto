import json
from datetime import timedelta

import requests
from _decimal import Decimal
from django.db.models import Q
from django.utils import timezone


from app.models import (Driver, GPSNumber, RentInformation, FleetOrder, CredentialPartner, ParkSettings, Fleet,
                        Partner, VehicleRent, Vehicle, DriverReshuffle)

from auto_bot.handlers.driver_manager.utils import find_reshuffle_period
from auto_bot.handlers.order.utils import check_reshuffle
from auto_bot.main import bot
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
        params = {
            'sid': self.get_session(),
            'svc': 'core/update_data_flags',
            'params': json.dumps({"spec": [{"type": "type",
                                            "data": "avl_unit",
                                            "flags": 1,
                                            "mode": 0}]})
        }
        response = requests.get(f"{self.get_base_url()}wialon/ajax.html", params=params)
        response_data = response.json()
        if 'error' in response_data:
            error_message = response_data['error']
            get_logger().error(error_message)
        for vehicle in response_data:
            data = {"name": vehicle['d']['nm'],
                    "partner": self.partner}
            obj, created = GPSNumber.objects.update_or_create(
                gps_id=vehicle['i'],
                defaults=data)
            Vehicle.objects.filter(
                partner=self.partner,
                licence_plate__icontains=data['name'],
                gps__isnull=True
            ).update(gps=obj)

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

    def get_driver_rent(self, start, end, driver, last_order):
        reshuffles = check_reshuffle(driver, start, end, gps=True)
        (rent_distance, rent_time), _, previous_finish_time = self.get_rent_stats(reshuffles, start, end, driver, False, last_order)
        return rent_distance, rent_time, previous_finish_time

    def get_road_distance(self, start, end, last_order, schema_drivers=None):
        road_dict = {}
        if not schema_drivers:
            schema_drivers = DriverReshuffle.objects.filter(
                partner=self.partner, swap_time__range=(start, end),
                driver_start__isnull=False).values_list(
                'driver_start', flat=True)
        drivers = Driver.objects.filter(pk__in=schema_drivers, schema__isnull=False)
        for driver in drivers:
            road_dict[driver] = self.get_driver_rent(start, end, driver, last_order)
        return road_dict

    def get_order_distance(self, orders):
        batch_params = []
        updated_orders = []
        bad_orders = []
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
                if (order.fleet_distance and
                        Decimal(distance) - order.fleet_distance > ParkSettings.get_value("Non-efficient", 8)):
                    bad_orders.append(order)
            orders_text = "\n".join([f"{order.driver}({timezone.localtime(order.accepted_time)}) "
                                     f"дистанція за агрегатором - {order.fleet_distance}, gps - {order.distance}"
                                     for order in bad_orders])
            if orders_text:
                bot.send_message(chat_id=ParkSettings.get_value("DEVELOPER_CHAT_ID"), text=orders_text)
            FleetOrder.objects.bulk_update(updated_orders, fields=['distance', 'road_time'], batch_size=200)

    def get_rent_stats(self, reshuffles, start_time, end_time, driver_pk, info_message, last_order):
        result_slots = []
        parameters = []
        prev_order_end_time = None
        for reshuffle in reshuffles:
            start, end = find_reshuffle_period(reshuffle, start_time, end_time)
            empty_time_slots, prev_order_end_time = self.get_time_without_orders(driver_pk, start, end, last_order)
            for slot in empty_time_slots:
                parameters.append(self.get_params_for_report(self.get_timestamp(slot[0]),
                                                             self.get_timestamp(slot[1]),
                                                             reshuffle.swap_vehicle.gps.gps_id))
            result_slots.extend(empty_time_slots)
        result = self.generate_batch_report(parameters, info_message)
        return result, result_slots, prev_order_end_time

    @staticmethod
    def get_time_without_orders(driver_pk, start, end, last_order):
        empty_time_slots = []
        prev_order_end_time = start
        orders = FleetOrder.objects.filter(
            Q(driver=driver_pk) &
            Q(state=FleetOrder.COMPLETED) &
            (Q(accepted_time__range=(start, end)) |
             Q(accepted_time__lt=start, finish_time__gt=start))).order_by('accepted_time')

        if orders.exists():
            for order in orders:
                if prev_order_end_time < order.accepted_time:
                    empty_time_slots.append((prev_order_end_time, timezone.localtime(order.accepted_time)))
                elif prev_order_end_time > order.finish_time:
                    continue
                prev_order_end_time = timezone.localtime(order.finish_time)
            if prev_order_end_time < end and not last_order:
                empty_time_slots.append((prev_order_end_time, end))
        else:
            empty_time_slots.append((start, end))
        return empty_time_slots, prev_order_end_time

    def get_vehicle_rent(self, start, end, driver, rent_distance):
        no_vehicle_gps = []
        reshuffles = check_reshuffle(driver, start, end)
        unique_vehicle_count = reshuffles.values('swap_vehicle').distinct().count()
        if unique_vehicle_count == 1:
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
                parameters = []
                if reshuffle.swap_vehicle.gps:
                    start_period, end_period = find_reshuffle_period(reshuffle, start, end)
                    no_orders_time = self.get_time_without_orders(driver, start_period, end_period, False)[0]
                    for slot in no_orders_time:
                        parameters.append(self.get_params_for_report(self.get_timestamp(slot[0]),
                                                                     self.get_timestamp(slot[1]),
                                                                     reshuffle.swap_vehicle.gps.gps_id))
                    rent_distance, _ = self.generate_batch_report(parameters)
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
        distance, road_time = self.generate_report(self.get_params_for_report(self.get_timestamp(start),
                                                                   self.get_timestamp(end),
                                                                   gps_id,
                                                                   self.get_session()))
        return distance, road_time

    def calc_total_km(self, driver, start, end):
        driver_vehicles = []
        total_km = 0
        road_time = timedelta()
        reshuffles = check_reshuffle(driver, start, end, gps=True)
        for reshuffle in reshuffles:
            driver_vehicles.append(reshuffle.swap_vehicle)
            start_report, end_report = find_reshuffle_period(reshuffle, start, end)
            km, in_order_time = self.total_per_day(reshuffle.swap_vehicle.gps.gps_id,
                                           start_report,
                                           end_report)
            total_km += km
            road_time += in_order_time
        return total_km, road_time, driver_vehicles

    def calculate_driver_vehicle_rent(self, start, end, driver, result):
        rent_distance, rent_time = result[0], result[1]
        data = {
            "report_from": start,
            "report_to": end,
            "driver": driver,
            "partner": self.partner,
            "rent_distance": rent_distance
        }
        driver_rent, created = RentInformation.objects.update_or_create(
            report_from__date=start,
            driver=driver,
            partner=self.partner,
            defaults=data)
        if not created:
            VehicleRent.objects.filter(report_from__range=(start, end),
                                       driver=driver, partner=self.partner).delete()
        no_gps_list = self.get_vehicle_rent(start, end, driver, rent_distance)
        return no_gps_list

    def save_daily_rent(self, start, end, drivers):
        in_road = self.get_road_distance(start, end, last_order=False, schema_drivers=drivers)
        no_vehicle_gps = []
        for driver, result in in_road.items():
            no_gps_list = self.calculate_driver_vehicle_rent(start, end, driver, result)
            no_vehicle_gps.extend(no_gps_list)
        if no_vehicle_gps:
            result_string = ', '.join([str(obj) for obj in set(no_vehicle_gps)])
            bot.send_message(chat_id=ParkSettings.get_value("DEVELOPER_CHAT_ID"),
                             text=f"У авто {result_string} відсутній gps")
