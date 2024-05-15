from datetime import datetime, time
import mimetypes
import time as tm
from io import BytesIO
from urllib import parse
import requests
from _decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist
from django.core.files import File
from django.db.models import Q, Case, When, Value, F
from django.utils import timezone

from django.db import models, transaction
from requests import JSONDecodeError

from app.models import BoltService, Driver, FleetsDriversVehiclesRate, FleetOrder, \
    CredentialPartner, Vehicle, PaymentTypes, Fleet, CustomReport, WeeklyReport, DailyReport, ParkSettings
from auto import settings

from auto_bot.handlers.order.utils import check_vehicle, normalized_plate
from scripts.redis_conn import redis_instance, get_logger
from selenium_ninja.synchronizer import Synchronizer, AuthenticationError, BoltException


class BoltRequest(Fleet, Synchronizer):
    base_url = models.URLField(default=BoltService.get_value('REQUEST_BOLT_LOGIN_URL'))

    def create_session(self, partner=None, password=None, login=None):
        partner_id = partner if partner else self.partner.id
        if self.partner and not self.deleted_at:
            login = CredentialPartner.get_value("BOLT_NAME", partner=partner_id)
            password = CredentialPartner.get_value("BOLT_PASSWORD", partner=partner_id)
        payload = {
            'username': login,
            'password': password,
            'device_name': "Chrome",
            'device_os_version': "NT 10.0",
            "device_uid": "6439b6c1-37c2-4736-b898-cb2a8608e6e2"
        }
        response = requests.post(url=f'{self.base_url}startAuthentication',
                                 params=self.param(),
                                 json=payload)
        if response.json()["code"] == 66610:
            raise AuthenticationError(f"{self.name} login or password incorrect.")
        else:
            refresh_token = response.json()["data"]["refresh_token"]
            redis_instance().set(f"{partner_id}_{self.name}_refresh", refresh_token)
            return True

    def get_header(self):
        token = redis_instance().get(f"{self.partner.id}_{self.name}_access")
        headers = {'Authorization': f'Bearer {token}'}
        return headers

    @staticmethod
    def param(limit=None):
        param = {"language": "uk-ua", "version": "FO.3.03", "brand": "bolt"}
        if limit:
            param.update({"limit": limit})
        return param

    def get_access_token(self):
        token = redis_instance().get(f"{self.partner.id}_{self.name}_refresh")
        park_id = redis_instance().get(f"{self.partner.id}_{self.name}_park_id")
        if token and park_id:
            access_payload = {
                "refresh_token": token,
                "company": {"company_id": park_id,
                            "company_type": "fleet_company"}
            }
            response = requests.post(url=f'{self.base_url}getAccessToken',
                                     params=self.param(),
                                     json=access_payload)
            if not response.json()['code']:
                redis_instance().set(f"{self.partner.id}_{self.name}_access", response.json()["data"]["access_token"])
        elif token:
            access_payload = {
                "refresh_token": token
            }
            response = requests.post(url=f'{self.base_url}getAccessToken',
                                     params=self.param(),
                                     json=access_payload)
            if not response.json()['code']:
                first_token = response.json()["data"]["access_token"]
                headers = {'Authorization': f'Bearer {first_token}'}
                response = requests.get(url=f'{self.base_url}getProfile',
                                        params=self.param(),
                                        headers=headers)
                if not response.json()['code']:
                    park_id = response.json()["data"]["companies"][0]["id"]
                    redis_instance().set(f"{self.partner.id}_{self.name}_park_id", park_id)
                    self.get_access_token()
        else:
            self.create_session()
            self.get_access_token()

    def get_target_url(self, url, params, json=None, method=None):
        http_methods = {
            "POST": requests.post
        }
        http_method_function = http_methods.get(method, requests.get)
        response = http_method_function(url, headers=self.get_header(), params=params, json=json)
        if response.json().get("code") in (999, 503):
            self.get_access_token()
            return self.get_target_url(url, params, json=json, method=method)
        try:
            if response.status_code == 404:
                raise BoltException(message=f"Not Found in {self.get_parent_function_name()}: "
                                            f"{response.json().get('message', url)}",
                                    url=url,
                                    method=self.get_parent_function_name())
            return response.json()
        except JSONDecodeError:
            message = f"Failed to decode JSON response for URL in {self.get_parent_function_name()}: {url}",
            raise BoltException(message=message,
                                url=url,
                                method=self.get_parent_function_name())

    def get_list_result(self, url, param, **kwargs):
        result = []
        offset = 0
        while True:
            param["offset"] = offset
            response = self.get_target_url(url, param)
            tm.sleep(0.5)
            result.extend(response[kwargs['data']][kwargs['list']])
            if param['limit'] + offset < response[kwargs['data']][kwargs['total']]:
                offset += param['limit']
            else:
                break
        return result

    def parse_json_report(self, start, end, driver_report):
        driver = FleetsDriversVehiclesRate.objects.get(driver_external_id=str(driver_report['id']),
                                                       fleet=self,
                                                       partner=self.partner).driver
        rides = FleetOrder.objects.filter(fleet=self.name,
                                          accepted_time__gte=start,
                                          accepted_time__lt=end,
                                          state=FleetOrder.COMPLETED,
                                          driver=driver).count()
        vehicle = check_vehicle(driver, end)
        report = {
            "report_from": start,
            "report_to": end,
            "fleet": self,
            "driver": driver,
            "total_amount_cash": driver_report['cash_in_hand'],
            "total_amount": driver_report['gross_revenue'],
            "tips": driver_report['tips'],
            "partner": self.partner,
            "bonuses": driver_report['bonuses'],
            "cancels": driver_report['cancellation_fees'],
            "fee": -(driver_report['gross_revenue'] - driver_report['net_earnings']),
            "total_amount_without_fee": driver_report['net_earnings'] - driver_report['bonuses'],
            "compensations": driver_report['compensations'],
            "refunds": driver_report['expense_refunds'],
            "total_rides": rides,
            "vehicle": vehicle
        }
        return report

    def save_daily_custom(self, start, end, driver_ids):
        param = self.param(50)
        param.update({"period": "ongoing_day"})
        request_url = f"{self.base_url}getDriverEarnings/recent"
        reports = self.get_list_result(request_url, param, data='data', list='drivers', total='total_rows')
        for driver_report in reports:
            if not driver_report['net_earnings'] or str(driver_report['id']) not in driver_ids:
                continue
            report = self.parse_json_report(start, end, driver_report)
            CustomReport.objects.update_or_create(report_from=start,
                                                  driver=report['driver'],
                                                  fleet=self,
                                                  partner=self.partner,
                                                  defaults=report
                                                  )

    def save_custom_report(self, start, end, driver_ids):
        param = self.param(50)
        format_start = start.strftime("%Y-%m-%d")
        format_end = end.strftime("%Y-%m-%d")
        param.update({"start_date": format_start,
                      "end_date": format_end
                      })
        request_url = f"{self.base_url}getDriverEarnings/dateRange"
        reports = self.get_list_result(request_url, param, data='data', list='drivers', total='total_rows')
        for driver_report in reports:
            if not driver_report['net_earnings'] or str(driver_report['id']) not in driver_ids:
                continue
            report = self.parse_json_report(start, end, driver_report)
            start_day = timezone.make_aware(datetime.combine(start, time.min))
            bolt_custom = CustomReport.objects.filter(report_from=start_day,
                                                      driver=report['driver'],
                                                      fleet=self,
                                                      partner=self.partner).last()
            if bolt_custom and bolt_custom.report_to != end:
                report.update(
                    {"report_from": bolt_custom.report_to,
                     "total_amount_cash": Decimal(driver_report['cash_in_hand']) - bolt_custom.total_amount_cash,
                     "total_amount": Decimal(driver_report['gross_revenue']) - bolt_custom.total_amount,
                     "tips": Decimal(driver_report['tips']) - bolt_custom.tips,
                     "bonuses": Decimal(driver_report['bonuses']) - bolt_custom.bonuses,
                     "cancels": Decimal(driver_report['cancellation_fees']) - bolt_custom.cancels,
                     "fee": Decimal(
                         -(driver_report['gross_revenue'] - driver_report['net_earnings'])) + bolt_custom.fee,
                     "total_amount_without_fee": Decimal(
                         driver_report['net_earnings'] - driver_report[
                             'bonuses']) - bolt_custom.total_amount_without_fee,
                     "compensations": Decimal(driver_report['compensations']) - bolt_custom.compensations,
                     "refunds": Decimal(driver_report['expense_refunds']) - bolt_custom.refunds,
                     })
            CustomReport.objects.update_or_create(report_from=start,
                                                  driver=report['driver'],
                                                  fleet=self,
                                                  partner=self.partner,
                                                  defaults=report
                                                  )

    def save_weekly_report(self, start, end, driver_ids):
        week_number = start.strftime('%GW%V')
        param = self.param(50)
        param["week"] = week_number
        request_url = f'{self.base_url}getDriverEarnings/week'
        reports = self.get_list_result(request_url, param, data='data', list='drivers', total='total_rows')
        for driver_report in reports:
            if str(driver_report['id']) not in driver_ids:
                continue
            report = self.parse_json_report(start, end, driver_report)
            report['total_amount_without_fee'] = driver_report['net_earnings']
            WeeklyReport.objects.update_or_create(report_from=start,
                                                  driver=report['driver'],
                                                  fleet=self,
                                                  partner=self.partner,
                                                  defaults=report)

    def save_daily_report(self, start, end, driver):
        format_start = start.strftime("%Y-%m-%d")
        format_end = end.strftime("%Y-%m-%d")
        param = self.param()
        param.update({"start_date": format_start,
                      "end_date": format_end,
                      "limit": 50})
        offset = 0
        limit = param['limit']
        bolt_reports = []
        while True:
            param["offset"] = offset
            reports = self.get_target_url(f'{self.base_url}getDriverEarnings/dateRange', param)
            for driver_report in reports['data']['drivers']:
                report = self.parse_json_report(start, end, driver_report)
                db_report, _ = DailyReport.objects.update_or_create(report_from=start,
                                                                    driver=driver,
                                                                    fleet=self,
                                                                    partner=self.partner,
                                                                    defaults=report)
                bolt_reports.append(db_report)
            if limit + offset < reports['data']['total_rows']:
                offset += limit
            else:
                break
        return bolt_reports

    def get_bonuses_info(self, driver, start, end):
        tm.sleep(0.5)
        driver_ids = Driver.objects.get_active(fleetsdriversvehiclesrate__fleet=self).values_list(
            'fleetsdriversvehiclesrate__driver_external_id', flat=True)
        compensations = 0
        format_start = start.strftime("%Y-%m-%d")
        format_end = end.strftime("%Y-%m-%d")
        param = self.param()
        param.update({"start_date": format_start,
                      "end_date": format_end,
                      "offset": 0,
                      "search": f"{driver.name} {driver.second_name}",
                      "limit": 50})
        reports = self.get_target_url(f'{self.base_url}getDriverEarnings/dateRange', param)
        if reports['data']['drivers']:
            for report in reports['data']['drivers']:
                if report['id'] in driver_ids:
                    compensations = report['compensations']
        return compensations

    def get_drivers_table(self):
        driver_list = []
        start = end = datetime.now().strftime('%Y-%m-%d')
        params = self.param(100)
        params.update({"start_date": start, "end_date": end})
        request_url = f'{self.base_url}getDriverEngagementData/dateRange'
        drivers = self.get_list_result(request_url, params, data='data', list='rows', total='total_rows')
        for driver in drivers:
            driver_params = self.param().copy()
            driver_params['id'] = driver['id']
            driver_info = self.get_target_url(f'{self.base_url}getDriver', driver_params)
            if driver_info['message'] != 'OK':
                tm.sleep(0.5)
                try:
                    driver_info = self.get_target_url(f'{self.base_url}getDriver', driver_params)
                except Exception as e:
                    get_logger().error(f"log_error is {e}")
            driver_list.append({
                'name': driver_info['data']['first_name'],
                'second_name': driver_info['data']['last_name'],
                'email': driver_info['data']['email'],
                'phone_number': driver_info['data']['phone'],
                'driver_external_id': driver_info['data']['id'],
                'pay_cash': driver['has_cash_payment']
            })
        return driver_list

    def get_vehicles(self):
        vehicles_list = []
        start = end = datetime.now().strftime('%Y-%m-%d')
        params = self.param(50)
        params.update({"start_date": start, "end_date": end})
        request_url = f'{self.base_url}getCarsPaginated'
        vehicles = self.get_list_result(request_url, params, data='data', list='rows', total='total_rows')
        for vehicle in vehicles:
            vehicles_list.append({
                'licence_plate': vehicle['reg_number'],
                'vehicle_name': vehicle['model'],
            })

        return vehicles_list

    def get_orders_list(self, start, end):
        format_start = start.strftime("%Y-%m-%d")
        format_end = end.strftime("%Y-%m-%d")
        payload = {
            "offset": 0,
            "limit": 100,
            "from_date": format_start,
            "to_date": format_end,
            "orders_state_statuses": [
                "client_did_not_show",
                "finished",
                "client_cancelled",
                "driver_did_not_respond",
                "driver_cancelled_after_accept",
                "driver_rejected"
            ]
        }
        offset = 0
        limit = payload["limit"]
        orders = []
        while True:
            payload["offset"] = offset
            report = self.get_target_url(f'{self.base_url}getOrdersHistory', self.param(), payload, method="POST")
            if report.get('data'):
                orders.extend(report['data']['rows'])
                if offset + limit < report['data']['total_rows']:
                    offset += limit
                    tm.sleep(0.5)
                else:
                    break
            else:
                break
        return orders

    def get_fleet_orders(self, start, end, driver=None, driver_ids=None):
        batch_data = []
        bolt_states = {
            "client_did_not_show": FleetOrder.CLIENT_CANCEL,
            "finished": FleetOrder.COMPLETED,
            "client_cancelled": FleetOrder.CLIENT_CANCEL,
            "driver_cancelled_after_accept": FleetOrder.DRIVER_CANCEL,
            "driver_did_not_respond": FleetOrder.DRIVER_CANCEL,
            "driver_rejected": FleetOrder.DRIVER_CANCEL
        }
        orders = self.get_orders_list(start, end)
        order_time = [timezone.make_aware(datetime.fromtimestamp(order['order_stops'][0]['arrived_at']))
                      if order['search_category']['id'] == 4878 and order['order_try_state'] == 'finished' else
                      timezone.make_aware(datetime.fromtimestamp(order['driver_assigned_time']))
                      for order in orders]
        filter_condition = Q(date_order__in=order_time,
                             order_id__in=[order['order_id'] for order in orders],
                             partner=self.partner)
        db_orders = FleetOrder.objects.filter(filter_condition)
        existing_orders = db_orders.values_list('order_id', flat=True)
        zero_price_orders = db_orders.filter(Q(price=0)).values_list('order_id', flat=True)
        zero_filtered = [order for order in orders if str(order['order_id']) in zero_price_orders]
        order_prices_dict = {order['order_id']: (order.get('total_price', 0), order.get("tip", 0))
                             for order in zero_filtered}
        zero_price_orders.update(
            price=Case(
                *[When(order_id=str(order_id), then=Value(total_price[0])) for order_id, total_price in
                  order_prices_dict.items()],
                default=F('price')
            ),
            tips=Case(
                *[When(order_id=str(order_id), then=Value(total_price[1])) for order_id, total_price in
                  order_prices_dict.items()],
                default=F('tips')
            )
        )
        calendar_errors = {}
        filtered_orders = [order for order in orders if str(order['order_id']) not in existing_orders]
        for order in filtered_orders:
            if driver and driver.get_driver_external_id(self) != str(order['driver_id']):
                continue
            driver_query = Driver.objects.filter(
                fleetsdriversvehiclesrate__driver_external_id=str(order['driver_id']),
                fleetsdriversvehiclesrate__fleet=self, partner=self.partner)
            if driver_query.exists():
                driver_order = driver_query.first()
                price = order.get('total_price', 0)
                tip = order.get("tip", 0)
                date_order = (timezone.make_aware(datetime.fromtimestamp(order['order_stops'][0]['arrived_at'])) if
                              order['search_category']['id'] == 4878 and order['order_try_state'] == 'finished' else
                              timezone.make_aware(datetime.fromtimestamp(order['driver_assigned_time'])))
                calendar_vehicle = check_vehicle(driver_order, date_time=date_order)
                vehicle = Vehicle.objects.filter(licence_plate=normalized_plate(order['car_reg_number'])).first()
                if calendar_vehicle != vehicle and not calendar_errors.get(driver_order.pk):
                    calendar_errors[driver_order.pk] = vehicle.licence_plate
                try:
                    finish = timezone.make_aware(
                        datetime.fromtimestamp(order['order_stops'][-1]['arrived_at']))
                except TypeError:
                    finish = None
                data = {"order_id": order['order_id'],
                        "fleet": self.name,
                        "driver": driver_order,
                        "from_address": order['pickup_address'],
                        "accepted_time": date_order,
                        "state": bolt_states.get(order['order_try_state']),
                        "finish_time": finish,
                        "payment": PaymentTypes.map_payments(order['payment_method']),
                        "destination": order['order_stops'][-1]['address'],
                        "vehicle": calendar_vehicle,
                        "price": price,
                        "tips": tip,
                        "partner": self.partner,
                        "date_order": date_order
                        }

                fleet_order = FleetOrder(**data)
                batch_data.append(fleet_order)
        with transaction.atomic():
            FleetOrder.objects.bulk_create(batch_data)
        return calendar_errors

    def get_drivers_status(self, photo=None):
        with_client = wait = Driver.objects.none()

        report = self.get_target_url(f'{self.base_url}getDriversForLiveMap', self.param())
        if report.get('data'):
            for driver in report['data']['list']:
                db_driver = Driver.objects.filter(
                                fleetsdriversvehiclesrate__driver_external_id=str(driver['id']),
                                fleetsdriversvehiclesrate__fleet=self, partner=self.partner)
                if db_driver.exists():
                    driver_obj = db_driver.first()
                    if driver['state'] == 'waiting_orders':
                        wait = wait.union(db_driver)

                    else:
                        with_client = with_client.union(db_driver)
                    if photo and driver_obj.photo == 'drivers/default-driver.png':
                        response = requests.get(driver['picture'])
                        if response.status_code == 200:
                            image_data = response.content
                            image_file = BytesIO(image_data)
                            driver_obj.photo = File(image_file,
                                                     name=f"{db_driver.name}_{db_driver.second_name}.jpg")
                            driver_obj.save(update_fields=["photo"])
                else:
                    continue
        return {'wait': wait,
                'with_client': with_client}

    def check_driver_status(self, driver):
        report = self.get_target_url(f'{self.base_url}getDriversForLiveMap', self.param())
        driver_id = driver.get_driver_external_id(self)
        if report.get('data') and driver_id:
            road_drivers = [rider['id'] for rider in report['data']['list'] if rider['state'] == 'has_order']
            if int(driver_id) in road_drivers:
                return True

    def disable_cash(self, driver_id, enable):
        payload = {
            "driver_id": driver_id,
            "has_cash_payment": enable
        }
        self.get_target_url(f'{self.base_url}driver/toggleCash', self.param(), payload, method="POST")
        result = FleetsDriversVehiclesRate.objects.filter(driver_external_id=driver_id).update(pay_cash=enable)
        return result

    def add_driver(self, job_application):
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        payload = {
            "email": f"{job_application.email}",
            "phone": f"{job_application.phone_number}",
            "referral_code": ""
        }
        response = self.get_target_url(f'{self.base_url}addDriverRegistration', self.param(), payload, method="POST")
        payload_form = {
            'hash': response['data']['hash'],
            'last_step': 'step_2',
            'first_name': job_application.first_name,
            'last_name': job_application.last_name,
            'email': job_application.email,
            'phone': job_application.phone_number,
            'birthday': '',
            'terms_consent_accepted': '0',
            'whatsapp_opt_in': '0',
            'city_data': 'Kyiv|ua|uk|634|₴|158',
            'city_id': '158',
            'language': 'uk',
            'referral_code': '',
            'has_car': '0',
            'allow_fleet_matching': '',
            'personal_code': '',
            'driver_license': '',
            'has_taxi_license': '0',
            'type': 'person',
            'license_type_selection': '',
            'company_name': '',
            'address': '',
            'reg_code': '',
            'company_is_liable_to_vat': '0',
            'vat_code': '',
            'beneficiary_name': '',
            'iban': '',
            'swift': '',
            'account_branch_code': '',
            'remote_training_url': '',
            'flow_id': '',
            'web_marketing_data[fbp]': '',
            'web_marketing_data[url]': f"{response['data']['registration_link']}/2",
            'web_marketing_data[user_agent]': '''Mozilla/5.0 (Windows NT 10.0; Win64; x64)
             AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36''',
            'is_fleet_company': '1'
        }

        encoded_payload = parse.urlencode(payload_form)
        params = {
            'version': 'DP.11.89',
            'hash': response['data']['hash'],
            'language': 'uk-ua',
        }
        second_params = dict(list(params.items())[:1])
        requests.post(f'{BoltService.get_value("R_BOLT_ADD_DRIVER_1")}register/',
                      params=second_params, headers=headers, data=encoded_payload)
        requests.get(f"{BoltService.get_value('R_BOLT_ADD_DRIVER_1')}getDriverRegistrationDocumentsSet/", params=params)

        file_paths = [
            f"{settings.MEDIA_URL}{job_application.driver_license_front}",  # license_front
            f"{settings.MEDIA_URL}{job_application.photo}",  # photo
            f"{settings.MEDIA_URL}{job_application.car_documents}",  # car_document
            f"{settings.MEDIA_URL}{job_application.insurance}"  # insurance
        ]

        payloads = [
            {'hash': response['data']['hash'], 'expires': str(job_application.license_expired)},
            {'hash': response['data']['hash']},
            {'hash': response['data']['hash']},
            {'hash': response['data']['hash'], 'expires': str(job_application.insurance_expired)}
        ]

        file_keys = [
            'ua_drivers_license',
            'ua_profile_pic',
            'ua_technical_passport',
            'ua_insurance_policy'
        ]

        for file_path, key, payload in zip(file_paths, file_keys, payloads):
            files = {}
            binary = requests.get(file_path).content
            mime_type, _ = mimetypes.guess_type(file_path)
            file_name = file_path.split('/')[-1]
            files[key] = (file_name, binary, mime_type)
            requests.post(f'{BoltService.get_value("R_BOLT_ADD_DRIVER_1")}uploadDriverRegistrationDocument/',
                          params=params, data=payload, files=files)
        payload_form['last_step'] = 'step_4'
        payload_form['web_marketing_data[url]'] = f"{response['data']['registration_link']}/4"
        encoded = parse.urlencode(payload_form)
        requests.post(f'{BoltService.get_value("R_BOLT_ADD_DRIVER_1")}register/', headers=headers,
                      params=params, data=encoded)
        job_application.status_bolt = datetime.now().date()
        job_application.save()


    def get_earnings_per_driver(self, driver, start, end):
        param = self.param()
        format_start, format_end = start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
        driver_id = driver.get_driver_external_id(self)
        total_amount, total_amount_cash = 0, 0

        if driver_id:
            param.update({"start_date": format_start,
                          "end_date": format_end,
                          "limit": 50,
                          "driverId": driver_id})

            request_url = f"{self.base_url}getDriverEarnings/dateRange"
            reports = self.get_list_result(request_url, param, data='data', list='drivers', total='total_rows')
            for driver_report in reports:
                if driver_report['id'] == int(driver_id):
                    total_amount += driver_report['net_earnings']
                    total_amount_cash += driver_report['cash_in_hand']

        return total_amount, total_amount_cash
