import json
from datetime import datetime, time
import requests
from _decimal import Decimal
from django.utils import timezone
from django.db import models
from requests import JSONDecodeError
from app.models import ParkSettings, FleetsDriversVehiclesRate, Driver, Service, FleetOrder, \
    CredentialPartner, Vehicle, PaymentTypes, CustomReport, Fleet, WeeklyReport, DailyReport
from auto_bot.handlers.order.utils import check_vehicle
from auto_bot.main import bot
from scripts.redis_conn import redis_instance
from selenium_ninja.synchronizer import Synchronizer, AuthenticationError


class UklonRequest(Fleet, Synchronizer):
    base_url = models.URLField(default=Service.get_value('UKLON_SESSION'))

    def get_header(self) -> dict:
        if not redis_instance().exists(f"{self.partner.id}_{self.name}_token"):
            self.get_access_token()
        token = redis_instance().get(f"{self.partner.id}_{self.name}_token")
        headers = {
            'Authorization': f'Bearer {token}'
        }
        return headers

    def park_payload(self, login, password) -> dict:
        if self.partner and not self.deleted_at:
            login = CredentialPartner.get_value(key='UKLON_NAME', partner=self.partner)
            password = CredentialPartner.get_value(key='UKLON_PASSWORD', partner=self.partner)
        payload = {
            'client_id': ParkSettings.get_value('CLIENT_ID_UKLON'),
            'client_secret': ParkSettings.get_value('CLIENT_SECRET_UKLON'),
            'contact': login,
            'device_id': "6648039b-0839-4588-9ead-57bdf63a6209",
            'grant_type': "password_mfa",
            'password': password,
        }
        return payload

    def uklon_id(self):
        if not redis_instance().exists(f"{self.partner.id}_park_id"):
            response = self.response_data(url=f"{self.base_url}me")
            redis_instance().set(f"{self.partner.id}_park_id", response['fleets'][0]['id'])
        return redis_instance().get(f"{self.partner.id}_park_id")

    def create_session(self, partner, login=None, password=None):
        payload = self.park_payload(login, password)
        response = requests.post(f"{self.base_url}auth", json=payload)
        if response.status_code == 201:
            token = response.json()["access_token"]
            refresh_token = response.json()["refresh_token"]
            redis_instance().set(f"{partner}_{self.name}_token", token)
            redis_instance().set(f"{partner}_{self.name}_refresh", refresh_token)
            return token
        elif response.status_code == 429:
            raise AuthenticationError(f"{self.name} service unavailable.")
        else:
            raise AuthenticationError(f"{self.name} login or password incorrect.")

    def get_access_token(self):
        refresh = redis_instance().get(f"{self.partner.id}_{self.name}_refresh")
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh,
            'client_id': ParkSettings.get_value('CLIENT_ID_UKLON'),
            'device_id': "6648039b-0839-4588-9ead-57bdf63a6209",
            "client_secret": ParkSettings.get_value('CLIENT_SECRET_UKLON')
        }
        response = requests.post(f"{self.base_url}auth", data=data)
        if response.status_code == 201:
            token = response.json()['access_token']
        else:
            bot.send_message(chat_id=515224934,
                             text=f"{self.partner} {response.status_code} create_session")
            token = self.create_session(self.partner.id)
        redis_instance().set(f"{self.partner.id}_{self.name}_token", token)

    @staticmethod
    def request_method(url: str = None,
                       headers: dict = None,
                       params: dict = None,
                       data: dict = None,
                       method: str = None):
        http_methods = {
            "POST": requests.post,
            "PUT": requests.put,
            "DELETE": requests.delete,
        }
        http_method_function = http_methods.get(method, requests.get)
        response = http_method_function(url=url, headers=headers, data=data, params=params)
        return response

    def response_data(self, url: str = None,
                      params: dict = None,
                      data=None,
                      headers: dict = None,
                      method: str = None) -> dict or None:

        response = self.request_method(url=url,
                                       params=params,
                                       headers=self.get_header() if headers is None else headers,
                                       data=data,
                                       method=method)
        if response.status_code in (401, 403):
            self.get_access_token()
            return self.response_data(url, params, data, headers, method)
        try:
            return response.json()
        except JSONDecodeError:
            return None

    @staticmethod
    def to_float(number: int, div=100) -> Decimal:
        return Decimal("{:.2f}".format(number / div))

    def find_value(self, data: dict, *args) -> Decimal:
        """Search value if args not False and return float"""
        nested_data = data
        for key in args:
            if key in nested_data:
                nested_data = nested_data[key]
            else:
                return Decimal(0)

        return self.to_float(nested_data)

    @staticmethod
    def find_value_str(data: dict, *args) -> str:
        """Search value if args not False and return str"""
        nested_data = data

        for key in args:
            if key in nested_data:
                nested_data = nested_data[key]
            else:
                return ''

        return nested_data

    def parse_json_report(self, start, end, driver, driver_report):
        vehicle = check_vehicle(driver, end, max_time=True)
        distance = driver_report.get('total_distance_meters', 0)
        report = {
            "report_from": start,
            "report_to": end,
            "vendor": self,
            "driver": driver,
            "total_rides": driver_report.get('total_orders_count', 0),
            "total_distance": self.to_float(distance, div=1000),
            "total_amount_cash": self.find_value(driver_report, *('profit', 'order', 'cash', 'amount')),
            "total_amount_on_card": self.find_value(driver_report, *('profit', 'order', 'wallet', 'amount')),
            "total_amount": self.find_value(driver_report, *('profit', 'order', 'total', 'amount')),
            "tips": self.find_value(driver_report, *('profit', 'tips', 'amount')),
            "bonuses": float(0),
            "fares": float(0),
            "fee": self.find_value(driver_report, *('loss', 'order', 'wallet', 'amount')),
            "total_amount_without_fee": self.find_value(driver_report, *('profit', 'total', 'amount')),
            "partner": self.partner,
            "vehicle": vehicle
        }
        return report, distance

    def generate_report(self, driver, start, end):
        driver_id = driver.get_driver_external_id(self.name)
        param = {'dateFrom': self.report_interval(start),
                 'dateTo': self.report_interval(end),
                 'limit': '50', 'offset': '0',
                 "driverId": driver_id
                 }
        url = f"{Service.get_value('UKLON_3')}{self.uklon_id()}"
        url += Service.get_value('UKLON_4')
        resp = self.response_data(url=url, params=param)
        data = resp.get('items')
        return data

    def save_custom_report(self, start, end, driver, custom=None):
        if custom:
            start_time = datetime.combine(start, time.min)
        else:
            start_time = start
        data = self.generate_report(driver, start_time, end)
        if data:
            for driver_report in data:
                report, distance = self.parse_json_report(start, end, driver, driver_report)
                if custom:
                    uklon_custom = CustomReport.objects.filter(report_from__date=start_time,
                                                               driver=driver,
                                                               vendor=self,
                                                               partner=self.partner).last()
                    if uklon_custom:
                        report.update({
                            "total_rides": driver_report.get('total_orders_count', 0) - uklon_custom.total_rides,
                            "total_distance": self.to_float(distance, div=1000) - uklon_custom.total_distance,
                            "total_amount_cash": (self.find_value(driver_report, *('profit', 'order', 'cash', 'amount')) -
                                                  uklon_custom.total_amount_cash),
                            "total_amount_on_card": (self.find_value(driver_report, *('profit', 'order', 'wallet', 'amount')) -
                                                     uklon_custom.total_amount_on_card),
                            "total_amount": (self.find_value(driver_report, *('profit', 'order', 'total', 'amount')) -
                                             uklon_custom.total_amount),
                            "tips": self.find_value(driver_report, *('profit', 'tips', 'amount')) - uklon_custom.tips,
                            "fee": self.find_value(driver_report, *('loss', 'order', 'wallet', 'amount')) - uklon_custom.fee,
                            "total_amount_without_fee": (self.find_value(driver_report, *('profit', 'total', 'amount')) -
                                                         uklon_custom.total_amount_without_fee),
                        })
                db_report = CustomReport.objects.filter(report_from=start,
                                                        driver=driver,
                                                        vendor=self,
                                                        partner=self.partner)
                db_report.update(**report) if db_report else CustomReport.objects.create(**report)

    def save_report(self, start, end, driver, model):
        data = self.generate_report(driver, start, end)
        if data:
            for driver_report in data:
                report = self.parse_json_report(start, end, driver, driver_report)[0]
                db_report, created = model.objects.get_or_create(report_from=start,
                                                                 driver=driver,
                                                                 vendor=self,
                                                                 partner=self.partner,
                                                                 defaults=report)
                if not created:
                    for key, value in report.items():
                        setattr(db_report, key, value)
                    db_report.save()
                return db_report

    def save_weekly_report(self, start, end, driver):
        return self.save_report(start, end, driver, WeeklyReport)

    def save_daily_report(self, start, end, driver):
        return self.save_report(start, end, driver, DailyReport)

    def get_earnings_per_driver(self, driver, start, end):
        driver_id = driver.get_driver_external_id(vendor=self.name)
        total_amount_without_fee = total_amount_cash = 0
        param = {'dateFrom': int(start.timestamp()),
                 'dateTo': int(end.timestamp()),
                 'limit': '50', 'offset': '0',
                 'driverId': driver_id
                 }
        url = f"{Service.get_value('UKLON_3')}{self.uklon_id()}"
        url += Service.get_value('UKLON_4')
        data = self.response_data(url=url, params=param)
        if data.get("items"):
            total_amount_cash = self.find_value(data["items"][0], *('profit', 'order', 'cash', 'amount'))
            total_amount_without_fee = self.find_value(data["items"][0], *('profit', 'total', 'amount'))
        return total_amount_without_fee, total_amount_cash

    def get_drivers_status(self):
        drivers = {
                'with_client': [],
                'wait': [],
            }
        url = f"{Service.get_value('UKLON_5')}{self.uklon_id()}"
        url += Service.get_value('UKLON_6')
        data = self.response_data(url, params={'limit': '50', 'offset': '0'})
        if data:
            for driver in data.get('data', []):
                name, second_name = driver['first_name'].split()[0], driver['last_name'].split()[0]
                first_data = (second_name, name)
                second_data = (name, second_name)
                if driver['status'] == 'Active':
                    drivers['wait'].append(first_data)
                    drivers['wait'].append(second_data)
                elif driver['status'] == 'OrderExecution':
                    drivers['with_client'].append(first_data)
                    drivers['with_client'].append(second_data)
        return drivers

    def get_drivers_table(self):
        drivers = []
        param = {'status': 'All',
                 'limit': '30',
                 'offset': '0'}
        url = f"{Service.get_value('UKLON_1')}{self.uklon_id()}"
        url_1 = url + Service.get_value('UKLON_6')
        url_2 = url + Service.get_value('UKLON_2')
        all_drivers = self.response_data(url=url_1, params=param)
        for driver in all_drivers['items']:
            pay_cash, vehicle_name, vin_code = True, '', ''
            if driver['restrictions']:
                pay_cash = False if 'Cash' in driver['restrictions'][0]['restriction_types'] else True
            elif self.find_value_str(driver, *('selected_vehicle',)):
                vehicle_name = f"{driver['selected_vehicle']['make']} {driver['selected_vehicle']['model']}"
                vin_code = self.response_data(f"{url_2}/{driver['selected_vehicle']['vehicle_id']}")
                vin_code = vin_code.get('vin_code', '')
            email = self.response_data(url=f"{url_1}/{driver['id']}")
            driver_data = self.response_data(
                url=f"{Service.get_value('UKLON_1')}{Service.get_value('UKLON_6')}/{driver['id']}/images",
                params={'image_size': 'sm'})
            drivers.append({
                'fleet_name': self.name,
                'name': driver['first_name'].split()[0],
                'second_name': driver['last_name'].split()[0],
                'email': email.get('email'),
                'phone_number': f"+{driver['phone']}",
                'driver_external_id': driver['id'],
                'photo': driver_data["driver_avatar_photo"]["url"],
                'pay_cash': pay_cash,
                'licence_plate': self.find_value_str(driver, *('selected_vehicle', 'license_plate')),
                'vehicle_name': vehicle_name,
                'vin_code': vin_code,
            })
        return drivers

    def get_fleet_orders(self, start, end, pk, driver_id):
        states = {"completed": FleetOrder.COMPLETED,
                  "Rider": FleetOrder.CLIENT_CANCEL,
                  "Driver": FleetOrder.DRIVER_CANCEL,
                  "System": FleetOrder.SYSTEM_CANCEL,
                  "Dispatcher": FleetOrder.SYSTEM_CANCEL
                  }

        driver = Driver.objects.get(pk=pk)
        str_driver_id = driver_id.replace("-", "")
        params = {"limit": 50,
                  "fleetId": self.uklon_id(),
                  "driverId": driver_id,
                  "from": self.report_interval(start),
                  "to": self.report_interval(end)
                  }
        orders = self.response_data(url=f"{Service.get_value('UKLON_1')}orders", params=params)
        try:
            for order in orders['items']:
                if (order['status'] in ("running", "accepted", "arrived") or
                        FleetOrder.objects.filter(order_id=order['id']).exists()):
                    continue
                vehicle = Vehicle.objects.get(licence_plate=order['vehicle']['licencePlate'])
                if check_vehicle(driver) != vehicle:
                    redis_instance().hset(f"wrong_vehicle_{self.partner.id}", pk, order['vehicle']['licencePlate'])
                detail = self.response_data(url=f"{Service.get_value('UKLON_1')}orders/{order['id']}",
                                            params={"driverId": str_driver_id})
                try:
                    finish_time = timezone.make_aware(datetime.fromtimestamp(detail["completedAt"]))
                except KeyError:
                    finish_time = None
                try:
                    start_time = timezone.make_aware(datetime.fromtimestamp(detail["createdAt"]))
                except KeyError:
                    start_time = None
                if order['status'] != "completed":
                    state = order["cancellation"]["initiator"]
                else:
                    state = order['status']
                data = {"order_id": order['id'],
                        "fleet": self.name,
                        "driver": driver,
                        "from_address": order['route']['points'][0]["address"],
                        "accepted_time": start_time,
                        "state": states.get(state),
                        "finish_time": finish_time,
                        "destination": order['route']['points'][-1]["address"],
                        "vehicle": vehicle,
                        "payment": PaymentTypes.map_payments(order['payment']['paymentType']),
                        "price": order['payment']['cost'],
                        "partner": self.partner
                        }
                obj, created = FleetOrder.objects.get_or_create(order_id=order['id'], defaults=data)
                if not created:
                    for key, value in data.items():
                        setattr(obj, key, value)
                    obj.save()
        except KeyError:
            bot.send_message(chat_id=ParkSettings.get_value("DEVELOPER_CHAT_ID"), text=f"{orders}")

    def disable_cash(self, driver_id, enable):
        url = f"{Service.get_value('UKLON_1')}{self.uklon_id()}"
        url += f'{Service.get_value("UKLON_6")}/{driver_id}/restrictions'
        headers = self.get_header()
        headers.update({"Content-Type": "application/json"})
        payload = {"type": "Cash"}
        method = 'DELETE' if enable else 'PUT'
        self.response_data(url=url,
                           headers=headers,
                           data=json.dumps(payload),
                           method=method)

        FleetsDriversVehiclesRate.objects.filter(driver_external_id=driver_id).update(pay_cash=enable)

    def withdraw_money(self):
        base_url = f"{Service.get_value('UKLON_1')}{self.uklon_id()}"
        url = base_url + f"{Service.get_value('UKLON_7')}"
        balance = {}
        items = []
        headers = self.get_header()
        headers.update({"Content-Type": "application/json"})
        resp = self.response_data(url, headers=headers)
        for driver in resp['items']:
            balance[driver['driver_id']] = driver['wallet']['balance']['amount'] -\
                                           int(ParkSettings.get_value('WITHDRAW_UKLON',
                                                                      partner=self.partner)) * 100
        for key, value in balance.items():
            if value > 0:
                items.append({
                    "employee_id": key,
                    "amount": {
                        "amount": value,
                        "currency": "UAH"
                    }})
        if items:
            url2 = base_url + f"{Service.get_value('UKLON_8')}"
            payload = {
                "items": items
            }
            self.response_data(url=url2, headers=headers, data=json.dumps(payload), method='POST')

    def detaching_the_driver_from_the_car(self, licence_plate):
        base_url = f"{Service.get_value('UKLON_1')}{self.uklon_id()}"
        url = base_url + Service.get_value('UKLON_2')
        params = {
            'limit': '30',
        }
        vehicles = self.response_data(url=url, params=params)
        matching_object = next((item for item in vehicles["data"] if item["licencePlate"] == licence_plate), None)
        if matching_object:
            id_vehicle = matching_object["id"]
            url += f"/{id_vehicle}/release"
            self.response_data(url=url, method='POST')

    def get_vehicles(self):
        vehicles = []
        param = {'limit': '30', 'offset': '0'}
        url = f"{Service.get_value('UKLON_1')}{self.uklon_id()}"
        url += Service.get_value('UKLON_2')
        all_vehicles = self.response_data(url=url, params=param)
        for vehicle in all_vehicles['data']:
            response = self.response_data(url=f"{url}/{vehicle['id']}")
            vehicles.append({
                'licence_plate': vehicle['licencePlate'],
                'vehicle_name': f"{vehicle['about']['maker']['name']} {vehicle['about']['model']['name']}",
                'vin_code': response.get('vin_code', '')
            })
        return vehicles
