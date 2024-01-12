from datetime import datetime
import mimetypes
import time
from urllib import parse
import requests
from _decimal import Decimal
from django.utils import timezone

from django.db import models
from app.models import BoltService, Driver, FleetsDriversVehiclesRate, FleetOrder, \
    CredentialPartner, Vehicle, PaymentTypes, Fleet, CustomReport, WeeklyReport, DailyReport
from auto import settings
from auto_bot.handlers.order.utils import check_vehicle
from scripts.redis_conn import redis_instance
from selenium_ninja.synchronizer import Synchronizer, AuthenticationError


class BoltRequest(Fleet, Synchronizer):
    base_url = models.URLField(default=BoltService.get_value('REQUEST_BOLT_LOGIN_URL'))

    def create_session(self, partner=None, login=None, password=None):
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

    def get_header(self):
        token = redis_instance().get(f"{self.partner.id}_{self.name}_access")
        headers = {'Authorization': f'Bearer {token}'}
        return headers

    @staticmethod
    def param():
        return {"language": "uk-ua", "version": "FO.3.03"}

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
        return response.json()

    def parse_json_report(self, start, end, driver, driver_report):
        rides = FleetOrder.objects.filter(fleet=self.name,
                                          accepted_time__gte=start,
                                          accepted_time__lt=end,
                                          state=FleetOrder.COMPLETED,
                                          driver=driver).count()
        vehicle = check_vehicle(driver, end, max_time=True)
        report = {
            "report_from": start,
            "report_to": end,
            "vendor": self,
            "driver": driver,
            "total_amount_cash": driver_report['cash_in_hand'],
            "total_amount": driver_report['gross_revenue'],
            "tips": driver_report['tips'],
            "partner": self.partner,
            "bonuses": driver_report['bonuses'],
            "cancels": driver_report['cancellation_fees'],
            "fee": -(driver_report['gross_revenue'] - driver_report['net_earnings']),
            "total_amount_without_fee": driver_report['net_earnings'],
            "compensations": driver_report['compensations'],
            "refunds": driver_report['expense_refunds'],
            "total_rides": rides,
            "vehicle": vehicle
        }
        return report

    def save_custom_report(self, start, end, driver, custom=None):
        time.sleep(0.5)
        param = self.param()
        if not custom:
            param.update({"period": "ongoing_day",
                          "search": str(driver),
                          "offset": 0,
                          "limit": 50})
            reports = self.get_target_url(f'{self.base_url}getDriverEarnings/recent', param)
        else:
            format_start = start.strftime("%Y-%m-%d")
            format_end = end.strftime("%Y-%m-%d")
            param.update({"start_date": format_start,
                          "end_date": format_end,
                          "search": str(driver),
                          "offset": 0,
                          "limit": 50})
            reports = self.get_target_url(f'{self.base_url}getDriverEarnings/dateRange', param)
        for driver_report in reports['data']['drivers']:
            report = self.parse_json_report(start, end, driver, driver_report)
            if custom:
                bolt_custom = CustomReport.objects.filter(report_from__date=start,
                                                          driver=driver,
                                                          vendor=self,
                                                          partner=self.partner).last()
                if bolt_custom:
                    report.update(
                        {"total_amount_cash": driver_report['cash_in_hand'] - bolt_custom.total_amount_cash,
                         "total_amount": driver_report['gross_revenue'] - bolt_custom.total_amount,
                         "tips": driver_report['tips'] - bolt_custom.tips,
                         "bonuses": driver_report['bonuses'] - bolt_custom.bonuses,
                         "cancels": driver_report['cancellation_fees'] - bolt_custom.cancels,
                         "fee": Decimal(
                             -(driver_report['gross_revenue'] - driver_report['net_earnings'])) + bolt_custom.fee,
                         "total_amount_without_fee": Decimal(
                             driver_report['net_earnings']) - bolt_custom.total_amount_without_fee,
                         "compensations": Decimal(driver_report['compensations']) - bolt_custom.compensations,
                         "refunds": Decimal(driver_report['expense_refunds']) - bolt_custom.refunds,
                         })
            db_report = CustomReport.objects.filter(report_from=start,
                                                    driver=driver,
                                                    vendor=self,
                                                    partner=self.partner)
            db_report.update(**report) if db_report else CustomReport.objects.create(**report)

    def save_weekly_report(self, start, end, driver):
        time.sleep(0.5)
        week_number = start.strftime('%GW%V')
        param = self.param()
        param.update({"week": week_number,
                      "search": str(driver),
                      "offset": 0,
                      "limit": 50})
        reports = self.get_target_url(f'{self.base_url}getDriverEarnings/week', param)
        for driver_report in reports['data']['drivers']:
            report = self.parse_json_report(start, end, driver, driver_report)
            db_report, created = WeeklyReport.objects.get_or_create(report_from=start,
                                                                    driver=driver,
                                                                    vendor=self,
                                                                    partner=self.partner,
                                                                    defaults=report)
            if not created:
                for key, value in report.items():
                    setattr(db_report, key, value)
                db_report.save()
            return db_report

    def save_daily_report(self, start, end, driver):
        time.sleep(0.5)
        format_start = start.strftime("%Y-%m-%d")
        format_end = end.strftime("%Y-%m-%d")
        param = self.param()
        param.update({"start_date": format_start,
                      "end_date": format_end,
                      "search": str(driver),
                      "offset": 0,
                      "limit": 50})
        reports = self.get_target_url(f'{self.base_url}getDriverEarnings/dateRange', param)
        for driver_report in reports['data']['drivers']:
            report = self.parse_json_report(start, end, driver, driver_report)
            db_report, created = DailyReport.objects.get_or_create(report_from=start,
                                                                   driver=driver,
                                                                   vendor=self,
                                                                   partner=self.partner,
                                                                   defaults=report)
            if not created:
                for key, value in report.items():
                    setattr(db_report, key, value)
                db_report.save()
            return db_report

    def get_bonuses_info(self, driver, start, end):
        time.sleep(0.5)
        bonuses = 0
        compensations = 0
        format_start = start.strftime("%Y-%m-%d")
        format_end = end.strftime("%Y-%m-%d")
        param = self.param()
        param.update({"start_date": format_start,
                      "end_date": format_end,
                      "offset": 0,
                      "search": str(driver),
                      "limit": 50})
        reports = self.get_target_url(f'{self.base_url}getDriverEarnings/dateRange', param)
        if reports['data']['drivers']:
            report_driver = reports['data']['drivers'][0]
            bonuses = report_driver['bonuses']
            compensations = report_driver['compensations']
        return bonuses, compensations

    def get_drivers_table(self):
        driver_list = []
        start = end = datetime.now().strftime('%Y-%m-%d')
        params = {"start_date": start,
                  "end_date": end,
                  "offset": 0,
                  "limit": 25}
        params.update(self.param())
        report = self.get_target_url(f'{self.base_url}getDriverEngagementData/dateRange', params)
        drivers = report['data']['rows']
        for driver in drivers:
            driver_params = self.param().copy()
            driver_params['id'] = driver['id']
            driver_info = self.get_target_url(f'{self.base_url}getDriver', driver_params)
            if driver_info['message'] == 'OK':
                driver_list.append({
                    'fleet_name': self.name,
                    'name': driver_info['data']['first_name'],
                    'second_name': driver_info['data']['last_name'],
                    'email': driver_info['data']['email'],
                    'phone_number': driver_info['data']['phone'],
                    'driver_external_id': driver_info['data']['id'],
                    'pay_cash': driver_info['data']['has_cash_payment'],
                    'licence_plate': '',
                    'vehicle_name': '',
                    'vin_code': '',
                })
        return driver_list

    def get_fleet_orders(self, start, end, pk, driver_id):
        bolt_states = {
            "client_did_not_show": FleetOrder.CLIENT_CANCEL,
            "finished": FleetOrder.COMPLETED,
            "client_cancelled": FleetOrder.CLIENT_CANCEL,
            "driver_cancelled_after_accept": FleetOrder.DRIVER_CANCEL,
            "driver_rejected": FleetOrder.DRIVER_CANCEL
        }
        driver = Driver.objects.get(pk=pk)
        format_start = start.strftime("%Y-%m-%d")
        format_end = end.strftime("%Y-%m-%d")
        payload = {
            "offset": 0,
            "limit": 50,
            "from_date": format_start,
            "to_date": format_end,
            "driver_id": driver_id,
            "orders_state_statuses": [
                "client_did_not_show",
                "finished",
                "client_cancelled",
                "driver_cancelled_after_accept",
                "driver_rejected"
            ]
        }
        report = self.get_target_url(f'{self.base_url}getOrdersHistory', self.param(), payload, method="POST")
        time.sleep(0.5)
        if report.get('data'):
            for order in report['data']['rows']:
                check_order = FleetOrder.objects.filter(order_id=order['order_id'])
                price = order.get('total_price', 0)
                tip = order.get("tip", 0)
                if check_order.exists():
                    check_order.update(price=price, tips=tip)
                    continue
                vehicle = Vehicle.objects.get(licence_plate=order['car_reg_number'])
                if check_vehicle(driver) != vehicle:
                    redis_instance().hset(f"wrong_vehicle_{self.partner.id}", pk, order['car_reg_number'])
                try:
                    finish = timezone.make_aware(
                        datetime.fromtimestamp(order['order_stops'][-1]['arrived_at']))
                except TypeError:
                    finish = None
                data = {"order_id": order['order_id'],
                        "fleet": self.name,
                        "driver": driver,
                        "from_address": order['pickup_address'],
                        "accepted_time": timezone.make_aware(datetime.fromtimestamp(order['accepted_time'])),
                        "state": bolt_states.get(order['order_try_state']),
                        "finish_time": finish,
                        "payment": PaymentTypes.map_payments(order['payment_method']),
                        "destination": order['order_stops'][-1]['address'],
                        "vehicle": vehicle,
                        "price": price,
                        "tips": tip,
                        "partner": self.partner
                        }
                FleetOrder.objects.create(order_id=order['order_id'], defaults=data)

    def get_drivers_status(self):
        with_client = []
        wait = []
        report = self.get_target_url(f'{self.base_url}getDriversForLiveMap', self.param())
        if report.get('data'):
            for driver in report['data']['list']:
                name, second_name = driver['name'].split(' ')
                if driver['state'] == 'waiting_orders':
                    wait.append((name, second_name))
                    wait.append((second_name, name))
                else:
                    with_client.append((name, second_name))
                    with_client.append((second_name, name))
        return {'wait': wait,
                'with_client': with_client}

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

    def get_vehicles(self):
        vehicles_list = []
        start = end = datetime.now().strftime('%Y-%m-%d')
        params = {"start_date": start,
                  "end_date": end,
                  "offset": 0,
                  "limit": 25}
        params.update(self.param())
        response = self.get_target_url(f'{self.base_url}getCarsPaginated', params=params)
        vehicles = response['data']['rows']
        for vehicle in vehicles:
            vehicles_list.append({
                'licence_plate': vehicle['reg_number'],
                'vehicle_name': vehicle['model'],
                'vin_code': ''
            })
        return vehicles_list
