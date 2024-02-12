import json
from datetime import datetime, timedelta, time
import requests
from _decimal import Decimal
from django.utils import timezone
from telegram import ParseMode

from app.models import (Driver, GPSNumber, RentInformation, FleetOrder, CredentialPartner, ParkSettings, Fleet,
                        Partner, VehicleRent, DriverReshuffle)
from auto_bot.handlers.driver_manager.utils import get_today_statistic
from auto_bot.handlers.order.utils import check_reshuffle
from auto_bot.main import bot
from scripts.redis_conn import redis_instance, get_logger
from selenium_ninja.driver import SeleniumTools


class UaGpsSynchronizer(Fleet):

    @staticmethod
    def create_session(partner, login, password):
        partner_obj = Partner.objects.get(pk=partner)
        token = SeleniumTools(partner).create_gps_session(login, password, partner_obj.gps_url)
        return token

    def get_session(self):
        params = {
            'svc': 'token/login',
            'params': json.dumps({"token": CredentialPartner.get_value('UAGPS_TOKEN', partner=self.partner)})
        }
        response = requests.get(f"{self.partner.gps_url}wialon/ajax.html", params=params)
        if response.json().get("error"):
            if not redis_instance().exists(f"{self.partner.id}_remove_gps"):
                redis_instance().set(f"{self.partner.id}_remove_gps", response.json().get("error"), ex=86400)
            return
        redis_instance().delete(f"{self.partner.id}_remove_gps")
        return response.json()['eid']

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
            response = requests.post(f"{self.partner.gps_url}wialon/ajax.html", params=params)
            redis_instance().set(f"{self.partner.id}_gps_id", response.json()['items'][0]['id'])
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
            response = requests.get(f"{self.partner.gps_url}wialon/ajax.html", params=params)
            for vehicle in response.json():
                data = {"name": vehicle['d']['nm'],
                        "partner": self.partner}
                obj, created = GPSNumber.objects.get_or_create(gps_id=vehicle['i'],
                                                               defaults=data)
                if not created:
                    for key, value in data.items():
                        setattr(obj, key, value)
                    obj.save()

    def generate_report(self, start_time, end_time, vehicle_id):
        if not redis_instance().exists(f"{self.partner.id}_remove_gps"):
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
                'svc': 'report/exec_report',
                'sid': self.get_session(),
                'params': json.dumps(parameters)
            }
            report = requests.get(f"{self.partner.gps_url}wialon/ajax.html", params=params)
            raw_time = report.json()['reportResult']['stats'][4][1]
            clean_time = [int(i) for i in raw_time.split(':')]
            road_time = timedelta(hours=clean_time[0], minutes=clean_time[1], seconds=clean_time[2])
            raw_distance = report.json()['reportResult']['stats'][5][1]
            road_distance = Decimal(raw_distance.split(' ')[0])
            return road_distance, road_time

    @staticmethod
    def get_timestamp(timeframe):
        return int(timeframe.timestamp())

    def get_road_distance(self, start, end, schema=None):
        road_dict = {}
        drivers = Driver.objects.get_active(partner=self.partner, schema=schema) if schema \
            else DriverReshuffle.objects.filter(partner=1, swap_time__date=timezone.localtime()
                                                ).values_list('driver_start', flat=True)
        for driver in drivers:
            if RentInformation.objects.filter(report_to=end, driver=driver):
                continue
            completed = []
            reshuffles = check_reshuffle(driver, start, end)
            for reshuffle in reshuffles:
                start_report = timezone.localtime(reshuffle.swap_time)
                end_report = timezone.localtime(reshuffle.end_time)
                if start_report < start:
                    start_report = start
                if end_report > end:
                    end_report = end

                completed += FleetOrder.objects.filter(driver=driver,
                                                       state=FleetOrder.COMPLETED,
                                                       accepted_time__gte=start_report,
                                                       accepted_time__lt=end_report).order_by('accepted_time')
                road_distance, road_time, previous_finish_time = self.calculate_order_distance(completed, end)
                if start.time == time.min:
                    yesterday_order = FleetOrder.objects.filter(driver=driver,
                                                                finish_time__gt=start,
                                                                state=FleetOrder.COMPLETED,
                                                                accepted_time__lte=start).first()
                    if yesterday_order and yesterday_order.vehicle.gps:
                        try:
                            report = self.generate_report(self.get_timestamp(start),
                                                          self.get_timestamp(timezone.localtime(
                                                              yesterday_order.finish_time)),
                                                          yesterday_order.vehicle.gps.gps_id)
                        except AttributeError as e:
                            get_logger().error(e)
                            continue
                        road_distance += report[0]
                        road_time += report[1]
                road_dict[driver] = (road_distance, road_time, previous_finish_time)
        return road_dict

    def calculate_order_distance(self, orders, end):
        road_distance = 0
        road_time = timedelta()
        previous_finish_time = None
        for order in orders:
            end_report = order.finish_time if order.finish_time < end else end
            try:
                if previous_finish_time is None or order.accepted_time >= previous_finish_time:
                    if order.finish_time < end and int(order.distance):
                        report = (order.distance, order.road_time)
                    else:
                        report = self.generate_report(self.get_timestamp(timezone.localtime(order.accepted_time)),
                                                      self.get_timestamp(timezone.localtime(end_report)),
                                                      order.vehicle.gps.gps_id)
                elif order.finish_time <= previous_finish_time:
                    continue
                else:
                    report = self.generate_report(self.get_timestamp(timezone.localtime(previous_finish_time)),
                                                  self.get_timestamp(timezone.localtime(end_report)),
                                                  order.vehicle.gps.gps_id)
            except AttributeError as e:
                get_logger().error(e)
                continue
            previous_finish_time = end_report
            road_distance += report[0]
            road_time += report[1]
        return road_distance, road_time, previous_finish_time

    def get_vehicle_rent(self, start, end, schema=None):
        for driver in Driver.objects.get_active(partner=self.partner, schema=schema):
            reshuffles = check_reshuffle(driver, start, end)
            for reshuffle in reshuffles:
                if start > reshuffle.swap_time:
                    start_period, end_period = start, reshuffle.end_time
                elif reshuffle.end_time <= end:
                    start_period, end_period = reshuffle.swap_time, reshuffle.end_time
                else:
                    start_period, end_period = reshuffle.swap_time, end
                orders = FleetOrder.objects.filter(
                    driver=driver,
                    state=FleetOrder.COMPLETED,
                    accepted_time__range=(start_period, end_period)).order_by('accepted_time')
                road_distance = self.calculate_order_distance(orders, end)[0]
                total_km = self.total_per_day(reshuffle.swap_vehicle.gps.gps_id, start_period, end_period)
                rent_distance = total_km - road_distance
                data = {"report_from": start_period,
                        "report_to": end_period,
                        "rent_distance": rent_distance,
                        "vehicle": reshuffle.swap_vehicle,
                        "driver": driver,
                        "partner": self.partner}
                VehicleRent.objects.get_or_create(report_from=start_period,
                                                  report_to=end_period,
                                                  vehicle=reshuffle.swap_vehicle,
                                                  defaults=data)

    def total_per_day(self, gps_id, start, end):
        distance = self.generate_report(self.get_timestamp(start),
                                        self.get_timestamp(end),
                                        gps_id)[0]
        return distance

    def calc_total_km(self, driver, start, end):
        driver_vehicles = []
        total_km = 0
        reshuffles = check_reshuffle(driver, start, end)
        for reshuffle in reshuffles:
            driver_vehicles.append(reshuffle.swap_vehicle)
            start_report = reshuffle.swap_time
            end_report = reshuffle.end_time
            if reshuffle.swap_time < start:
                start_report = start
            if reshuffle.end_time > end:
                end_report = end
            try:
                total_km += self.total_per_day(reshuffle.swap_vehicle.gps.gps_id,
                                               start_report,
                                               end_report)
            except AttributeError as e:
                get_logger().error(e)
                continue
        return total_km, driver_vehicles

    def save_daily_rent(self, start, end, schema):
        self.get_vehicle_rent(start, end, schema)
        in_road = self.get_road_distance(start, end, schema)
        for driver, result in in_road.items():
            distance, road_time = result[0], result[1]
            total_km = self.calc_total_km(driver, start, end)[0]

            rent_distance = total_km - distance
            RentInformation.objects.create(report_from=start,
                                           report_to=end,
                                           driver=driver,
                                           partner=self.partner,
                                           rent_distance=rent_distance)

    def check_today_rent(self):
        start = timezone.make_aware(datetime.combine(timezone.localtime(), time.min))
        end = timezone.make_aware(datetime.combine(timezone.localtime(), time.max))
        in_road = self.get_road_distance(start, end)
        for driver, result in in_road.items():
            distance, road_time, end_time = result
            total_km = 0
            if not end_time:
                end_time = timezone.localtime()
            reshuffles = check_reshuffle(driver, start, end)
            for reshuffle in reshuffles:
                try:
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
                except AttributeError as e:
                    get_logger().error(e)
                    continue
            rent_distance = total_km - distance
            driver_obj = Driver.objects.get(id=driver)
            kasa, card, mileage, orders, canceled_orders = get_today_statistic(self.partner, start, end_time, driver_obj)
            time_now = timezone.localtime(end_time)
            if kasa and mileage:
                kasa_text = f'<font color="red">{kasa}</font>' if kasa/time_now.hour < 10 else kasa
                text = f"Поточна статистика на {time_now.strftime('%H:%M')}:\n" \
                       f"Водій: {driver_obj}\n"\
                       f"Каса: {kasa_text}\n"\
                       f"Виконано замовлень: {orders}\n"\
                       f"Скасовано замовлень: {canceled_orders}\n"\
                       f"Пробіг під замовленням: {mileage}\n"\
                       f"Ефективність: {round(kasa / mileage, 2)}\n"\
                       f"Холостий пробіг: {rent_distance}\n"
            else:
                text = f"Водій {driver_obj} ще не виконав замовлень\n" \
                       f"Холостий пробіг: {rent_distance}\n"
            if timezone.localtime(end_time).time() > time(7, 0):
                bot.send_message(chat_id=ParkSettings.get_value("DEVELOPER_CHAT_ID"),
                                 text=text, parse_mode=ParseMode.HTML)
