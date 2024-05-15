import json
import uuid
from datetime import datetime, time, timedelta
import requests
from _decimal import Decimal

from django.db.models import Q
from django.utils import timezone
from django.db import models, transaction
from requests import JSONDecodeError
from app.models import ParkSettings, FleetsDriversVehiclesRate, Service, FleetOrder, \
    CredentialPartner, Vehicle, PaymentTypes, CustomReport, Fleet, WeeklyReport, DailyReport, Driver
from auto_bot.handlers.order.utils import check_vehicle, normalized_plate
from auto_bot.main import bot
from scripts.redis_conn import redis_instance
from selenium_ninja.synchronizer import Synchronizer, AuthenticationError, CustomException, UklonException


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
        device_id = "6648039b-0839-4588-9ead-57bdf63a6209"
        if self.partner and not self.deleted_at:
            login = CredentialPartner.get_value(key='UKLON_NAME', partner=self.partner)
            password = CredentialPartner.get_value(key='UKLON_PASSWORD', partner=self.partner)
            device_id = ParkSettings.get_value(f'DEVICE_UKLON_{self.partner.id}', device_id)
        payload = {
            'client_id': ParkSettings.get_value('CLIENT_ID_UKLON'),
            'client_secret': ParkSettings.get_value('CLIENT_SECRET_UKLON'),
            'contact': login,
            'device_id': device_id,
            'grant_type': "password_mfa",
            'password': password,
        }
        return payload

    def uklon_id(self):
        if not redis_instance().exists(f"{self.partner.id}_park_id"):
            response = self.response_data(url=f"{self.base_url}/me")
            redis_instance().set(f"{self.partner.id}_park_id", response['fleets'][0]['id'])
        return redis_instance().get(f"{self.partner.id}_park_id")

    def create_session(self, partner, password=None, login=None):
        payload = self.park_payload(login, password)
        response = requests.post(f"{self.base_url}/auth", json=payload)
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
        device_id = ParkSettings.get_value(f'DEVICE_UKLON_{self.partner.id}',
                                           "6648039b-0839-4588-9ead-57bdf63a6209")
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh,
            'client_id': ParkSettings.get_value('CLIENT_ID_UKLON'),
            'device_id': device_id,
            "client_secret": ParkSettings.get_value('CLIENT_SECRET_UKLON')
        }
        response = requests.post(f"{self.base_url}/auth", data=data)
        if response.status_code == 201:
            token = response.json()['access_token']
        else:
            bot.send_message(chat_id=ParkSettings.get_value("DEVELOPER_CHAT_ID"),
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
            if response.status_code == 404:
                raise UklonException(message=f"Not Found in {self.get_parent_function_name()}: "
                                             f"{response.json().get('message', url)}",
                                     url=url,
                                     method=self.get_parent_function_name())
            return response.json()
        except JSONDecodeError:
            if self.get_parent_function_name() != 'disable_cash':
                raise UklonException(
                    message=f"Failed to decode JSON response for URL in {self.get_parent_function_name()}: {url}",
                    url=url,
                    method=self.get_parent_function_name())

    @staticmethod
    def to_float(number: int, div=100) -> Decimal:
        return Decimal("{:.2f}".format(number / div))

    def get_tips(self, order):
        return (self.to_float(order['additionalIncome']['tips']['amount']) +
                self.to_float(order['additionalIncome']['compensation']['amount']))

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
        vehicle = check_vehicle(driver, end)
        distance = driver_report.get('total_distance_meters', 0)
        report = {
            "report_from": start,
            "report_to": end,
            "fleet": self,
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

    def generate_report(self, param):
        url = f"{Service.get_value('UKLON_3')}/{self.uklon_id()}"
        url += Service.get_value('UKLON_4')
        resp = self.response_data(url=url, params=param)
        return resp

    def save_daily_custom(self, start, end, driver_ids):
        param = {'dateFrom': self.report_interval(start),
                 'dateTo': self.report_interval(end),
                 'limit': 50,
                 }
        offset = 0
        limit = param["limit"]
        while True:
            param['offset'] = offset
            data = self.generate_report(param)
            for driver_report in data['items']:
                if driver_report['driver']['id'] in driver_ids:
                    driver = FleetsDriversVehiclesRate.objects.get(
                        driver_external_id=driver_report['driver']['id'],
                        fleet=self, partner=self.partner).driver
                    report, distance = self.parse_json_report(start, end, driver, driver_report)
                    CustomReport.objects.update_or_create(report_from=start,
                                                          driver=driver,
                                                          fleet=self,
                                                          partner=self.partner,
                                                          defaults=report)
            if not data.get('has_more_items'):
                break
            elif offset + limit < data['total_count']:
                offset += limit
            else:
                break

    def save_custom_report(self, start, end, driver_ids):
        start_time = datetime.combine(start, time.min)
        param = {'dateFrom': self.report_interval(start_time),
                 'dateTo': self.report_interval(end),
                 'limit': 50,
                 }
        offset = 0
        limit = param["limit"]
        while True:
            param['offset'] = offset
            data = self.generate_report(param)
            for driver_report in data['items']:
                if driver_report['driver']['id'] in driver_ids:
                    driver = FleetsDriversVehiclesRate.objects.get(
                        driver_external_id=driver_report['driver']['id'],
                        fleet=self, partner=self.partner).driver
                    report, distance = self.parse_json_report(start, end, driver, driver_report)
                    start_day = timezone.make_aware(start_time)
                    uklon_custom = CustomReport.objects.filter(report_from=start_day,
                                                               driver=driver,
                                                               fleet=self,
                                                               partner=self.partner).last()
                    if uklon_custom and uklon_custom.report_to != end:
                        report.update({
                            "report_from": uklon_custom.report_to,
                            "total_rides": driver_report.get('total_orders_count', 0) - uklon_custom.total_rides,
                            "total_distance": self.to_float(distance, div=1000) - uklon_custom.total_distance,
                            "total_amount_cash": (
                                    self.find_value(driver_report, *('profit', 'order', 'cash', 'amount')) -
                                    uklon_custom.total_amount_cash),
                            "total_amount_on_card": (
                                    self.find_value(driver_report, *('profit', 'order', 'wallet', 'amount')) -
                                    uklon_custom.total_amount_on_card),
                            "total_amount": (self.find_value(driver_report, *('profit', 'order', 'total', 'amount')) -
                                             uklon_custom.total_amount),
                            "tips": self.find_value(driver_report, *('profit', 'tips', 'amount')) - uklon_custom.tips,
                            "fee": self.find_value(driver_report,
                                                   *('loss', 'order', 'wallet', 'amount')) - uklon_custom.fee,
                            "total_amount_without_fee": (
                                    self.find_value(driver_report, *('profit', 'total', 'amount')) -
                                    uklon_custom.total_amount_without_fee),
                        })
                    db_report = CustomReport.objects.filter(report_from=start,
                                                            driver=driver,
                                                            fleet=self,
                                                            partner=self.partner)
                    db_report.update(**report) if db_report else CustomReport.objects.create(**report)
            if not data.get('has_more_items'):
                break
            elif offset + limit < data['total_count']:
                offset += limit
            else:
                break

    def save_report(self, start, end, model):
        param = {'dateFrom': self.report_interval(start),
                 'dateTo': self.report_interval(end),
                 'limit': 50,
                 }
        offset = 0
        limit = param["limit"]
        reports = []
        while True:
            param['offset'] = offset
            data = self.generate_report(param)
            for driver_report in data['items']:
                driver = FleetsDriversVehiclesRate.objects.get(
                    driver_external_id=driver_report['driver']['id'],
                    fleet=self, partner=self.partner).driver
                report = self.parse_json_report(start, end, driver, driver_report)[0]
                db_report, created = model.objects.get_or_create(report_from=start,
                                                                 driver=driver,
                                                                 fleet=self,
                                                                 partner=self.partner,
                                                                 defaults=report)
                if not created:
                    for key, value in report.items():
                        setattr(db_report, key, value)
                    db_report.save()
                reports.append(db_report)
            if not data.get('has_more_items'):
                break
            elif offset + limit < data['total_count']:
                offset += limit
            else:
                break
        return reports

    def save_weekly_report(self, start, end, driver_ids):
        return self.save_report(start, end, WeeklyReport)

    def save_daily_report(self, start, end):
        return self.save_report(start, end, DailyReport)

    def get_earnings_per_driver(self, driver, start, end):
        total_amount_without_fee = total_amount_cash = 0
        driver_id = driver.get_driver_external_id(self)
        if (timezone.localtime() - end).total_seconds() > 60:
            end += timedelta(seconds=60)
        if driver_id:
            param = {'dateFrom': int(start.timestamp()),
                     'dateTo': int(end.timestamp()),
                     'limit': '50', 'offset': '0',
                     'driverId': driver_id
                     }
            url = f"{Service.get_value('UKLON_3')}/{self.uklon_id()}"
            url += Service.get_value('UKLON_4')
            data = self.response_data(url=url, params=param)
            if data.get("items"):
                total_amount_cash = self.find_value(data["items"][0], *('profit', 'order', 'cash', 'amount'))
                total_amount_without_fee = self.find_value(data["items"][0], *('profit', 'total', 'amount'))
        return total_amount_without_fee, total_amount_cash

    def get_drivers_status(self):
        with_client = wait = Driver.objects.none()
        url = f"{Service.get_value('UKLON_5')}/{self.uklon_id()}"
        url += Service.get_value('UKLON_6')
        data = self.response_data(url, params={'limit': '50', 'offset': '0'})
        for driver in data.get('data', []):
            db_driver = Driver.objects.filter(
                fleetsdriversvehiclesrate__driver_external_id=driver['id'],
                fleetsdriversvehiclesrate__fleet=self, partner=self.partner)
            if db_driver.exists():
                if driver['status'] == 'Active':
                    wait = wait.union(db_driver)
                elif driver['status'] == 'OrderExecution':
                    with_client = with_client.union(db_driver)
            else:
                continue
        return {'wait': wait,
                'with_client': with_client}

    def get_drivers_table(self):
        drivers = []
        param = {'status': 'All',
                 'block_status': 'All',
                 'limit': 30}
        url = f"{Service.get_value('UKLON_1')}/{self.uklon_id()}"
        url_1 = url + Service.get_value('UKLON_6')
        offset = 0
        limit = param["limit"]

        while True:
            param["offset"] = offset
            all_drivers = self.response_data(url=url_1, params=param)
            for driver in all_drivers['items']:
                email = self.response_data(url=f"{url_1}/{driver['id']}")
                driver_data = self.response_data(
                    url=f"{Service.get_value('UKLON_1')}{Service.get_value('UKLON_6')}/{driver['id']}/images",
                    params={'image_size': 'sm'})
                if driver['restrictions']:
                    manager_restrictions = next(
                        (item for item in driver["restrictions"] if item["restricted_by"] == "Manager"), None)
                    if manager_restrictions:
                        cash_result = next((item for item in manager_restrictions['restriction_items'] if
                                            item.get('fleet_id') == self.uklon_id()), None)
                        pay_cash = not bool(cash_result)
                    else:
                        pay_cash = True
                else:
                    pay_cash = True
                drivers.append({
                    'fleet_name': self.name,
                    'name': driver['first_name'].split()[0],
                    'second_name': driver['last_name'].split()[0],
                    'email': email.get('email'),
                    'phone_number': f"+{driver['phone']}",
                    'driver_external_id': driver['id'],
                    'photo': driver_data["driver_avatar_photo"]["url"],
                    'pay_cash': pay_cash
                })

            if offset + limit < all_drivers['total_count']:
                offset += limit
            else:
                break
        return drivers

    def get_fleet_orders(self, start, end, driver=None, driver_ids=None):
        states = {"completed": FleetOrder.COMPLETED,
                  "Rider": FleetOrder.CLIENT_CANCEL,
                  "Driver": FleetOrder.DRIVER_CANCEL,
                  "System": FleetOrder.SYSTEM_CANCEL,
                  "Dispatcher": FleetOrder.SYSTEM_CANCEL
                  }
        end_period = timezone.localtime() if end > timezone.localtime() else end
        params = {"limit": 100,
                  "fleetId": self.uklon_id(),
                  "from": self.report_interval(start),
                  "to": self.report_interval(end_period)
                  }
        batch_data = []
        orders = []
        while True:
            response = self.response_data(url=f"{Service.get_value('UKLON_1')}/orders", params=params)
            orders.extend(response.get('items', []))
            if response.get('cursor'):
                params['cursor'] = response['cursor']
            else:
                break
        filter_condition = Q(date_order__in=[
            timezone.make_aware(datetime.fromtimestamp(order["pickupTime"])) for order in orders
        ],
            order_id__in=[order['id'] for order in orders],
            partner=self.partner)
        orders_with_tips = [(order['id'], self.get_tips(order)) for order in orders if
                            order['additionalIncome']['tips']['amount'] or
                            order['additionalIncome']['compensation']['amount']]
        existing_orders = FleetOrder.objects.filter(filter_condition)
        existing_orders_ids = existing_orders.values_list('order_id', flat=True)
        existing_orders_no_tip = existing_orders.filter(tips=0)
        filtered_orders = [order for order in orders if order['id'] not in existing_orders_ids
                           and order['status'] not in ("running", "accepted", "arrived")]
        for order, tips in orders_with_tips:
            if order in existing_orders_no_tip.values_list('order_id', flat=True):
                existing_orders_no_tip.filter(order_id=order).update(tips=tips)
        calendar_errors = {}
        for order in filtered_orders:
            formatted_uuid = str(uuid.UUID(order['driver']['id']))
            if driver and driver.get_driver_external_id(self) != formatted_uuid:
                continue
            try:
                driver_order = Driver.objects.filter(
                    fleetsdriversvehiclesrate__driver_external_id=formatted_uuid,
                    fleetsdriversvehiclesrate__fleet=self, partner=self.partner).first()
                calendar_vehicle = check_vehicle(driver_order, timezone.make_aware(
                    datetime.fromtimestamp(order["pickupTime"])))
                vehicle = Vehicle.objects.get(licence_plate=normalized_plate(order['vehicle']['licencePlate']))
                if calendar_vehicle != vehicle and not calendar_errors.get(driver_order.pk):
                    calendar_errors[driver_order.pk] = vehicle.licence_plate
                finish_time = timezone.make_aware(datetime.fromtimestamp(order.get("completedAt"))) if order.get(
                    "completedAt") is not None else None
                start_time = timezone.make_aware(datetime.fromtimestamp(order.get("acceptedAt"))) if order.get(
                    "acceptedAt") is not None else None
                tips = self.get_tips(order)
                if order['status'] != "completed":
                    state = order["cancellation"]["initiator"]
                    price = 0
                    distance = 0
                else:
                    state = order['status']
                    price = order['payment']['cost']
                    distance = order['payment']['distance']
                data = {"order_id": order['id'],
                        "fleet": self.name,
                        "driver": driver_order,
                        "from_address": order['route']['points'][0]["address"],
                        "accepted_time": start_time,
                        "state": states.get(state),
                        "finish_time": finish_time,
                        "destination": order['route']['points'][-1]["address"],
                        "vehicle": calendar_vehicle,
                        "payment": PaymentTypes.map_payments(order['payment']['paymentType']),
                        "tips": tips,
                        "price": price,
                        "fleet_distance": distance,
                        "partner": self.partner,
                        "date_order": timezone.make_aware(datetime.fromtimestamp(order["pickupTime"]))
                        }
                fleet_order = FleetOrder(**data)
                batch_data.append(fleet_order)

            except KeyError:
                bot.send_message(chat_id=ParkSettings.get_value("DEVELOPER_CHAT_ID"), text=f"{order}")

        with transaction.atomic():
            FleetOrder.objects.bulk_create(batch_data)
        return calendar_errors

    def disable_cash(self, driver_id, enable):
        url = f"{Service.get_value('UKLON_1')}/{self.uklon_id()}"
        url += f'{Service.get_value("UKLON_6")}/{driver_id}/restrictions'
        headers = self.get_header()
        headers.update({"Content-Type": "application/json"})
        payload = {"type": "Cash"}
        method = 'DELETE' if enable else 'PUT'
        self.response_data(url=url,
                           headers=headers,
                           data=json.dumps(payload),
                           method=method)

        result = FleetsDriversVehiclesRate.objects.filter(driver_external_id=driver_id).update(pay_cash=enable)
        return result

    def withdraw_money(self):
        base_url = f"{Service.get_value('UKLON_1')}/{self.uklon_id()}"
        url = base_url + f"{Service.get_value('UKLON_7')}"
        balance = {}
        items = []
        headers = self.get_header()
        headers.update({"Content-Type": "application/json"})
        resp = self.response_data(url, headers=headers)
        for driver in resp['items']:
            balance[driver['driver_id']] = driver['wallet']['balance']['amount'] - \
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
        base_url = f"{Service.get_value('UKLON_1')}/{self.uklon_id()}"
        url = base_url + Service.get_value('UKLON_2')
        params = {
            'limit': 30,
        }
        vehicles = self.response_data(url=url, params=params)
        matching_object = next((item for item in vehicles["data"]
                                if normalized_plate(item["licencePlate"]) == licence_plate), None)
        if matching_object:
            id_vehicle = matching_object["id"]
            url += f"/{id_vehicle}/release"
            self.response_data(url=url, method='POST')

    def get_vehicles(self):
        vehicles = []
        param = {'limit': 30}
        offset = 0
        limit = param["limit"]

        while True:
            param["offset"] = offset
            url = f"{Service.get_value('UKLON_1')}/{self.uklon_id()}"
            url += Service.get_value('UKLON_2')
            all_vehicles = self.response_data(url=url, params=param)
            for vehicle in all_vehicles['data']:
                response = self.response_data(url=f"{url}/{vehicle['id']}")
                vehicles.append({
                    'licence_plate': vehicle['licencePlate'],
                    'vehicle_name': f"{vehicle['about']['maker']['name']} {vehicle['about']['model']['name']}",
                    'vin_code': response.get('vin_code', '')
                })

            if offset + limit < all_vehicles['total']:
                offset += limit
            else:
                break
        return vehicles
