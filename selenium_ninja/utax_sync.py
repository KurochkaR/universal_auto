import requests

from app.models import ParkSettings, Service838, Payments, Partner
from selenium_ninja.synchronizer import Synchronizer

class AuthenticationError(Exception):
    def __init__(self, message="Authentication error"):
        self.message = message
        super().__init__(self.message)

class Request838(Synchronizer):
    def __init__(self, partner_id=None, fleet="838"):
        super().__init__(partner_id, fleet)
        self.base_url = "https://ms.utaxcloud.net/partner/api/v1/"
        self.param = {"language": "uk-ua", "version": "FO.2.61"}

    def get_login_token(self):
        refresh_token = self.redis.get(f"{self.partner_id}_{self.fleet}_refresh")
        if not refresh_token:
            payload = {
                        'email': ParkSettings.get_value("838_NAME", partner=self.partner_id),
                        'password': ParkSettings.get_value("838_PASSWORD", partner=self.partner_id)
                       }
            response = requests.post(url=f"{self.base_url}token/create", json=payload)

        else:
            payload = {
                "refresh_token": refresh_token
            }
            response = requests.post(url=f"{self.base_url}token/refresh", json=payload)
        if response.status_code == 200:
            refresh_token = response.json()["data"]["refresh_token"]
            self.redis.set(f"{self.partner_id}_{self.fleet}_refresh", refresh_token)
            token = response.json()["data"]["access_token"]
            self.redis.set(f"{self.partner_id}_{self.fleet}_access", token)
            return token
        else:
            if refresh_token:
                self.redis.delete(f"{self.partner_id}_{self.fleet}_refresh")
                self.get_login_token()
            else:
                raise AuthenticationError("Wrong credentials")

    def get_access_token(self):
        token = self.redis.get(f"{self.partner_id}_{self.fleet}_access")
        if not token:
            try:
                token = self.get_login_token()
            except AuthenticationError:
                self.logger.error("Wrong credentials 838")
        return token

    def get_target_url(self, url, params=None):
        token = self.get_access_token()
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(url, params=params, headers=headers)
        if not response.status_code == 200:
            self.redis.delete(f"{self.partner_id}_{self.fleet}_access")
            token = self.get_access_token()
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.get(url, params=params, headers=headers)
        return response.json()

    def get_car_groups(self):
        groups = self.redis.hgetall(f"{self.partner_id}_{self.fleet}_groups")
        if not groups:
            response = self.get_target_url(url=f"{self.base_url}operator/info")
            groups = {}
            for group in response['data']['groups']:
                name = group["name"]
                group_id = group["id"]
                groups[name] = group_id
            self.redis.hmset(f"{self.partner_id}_{self.fleet}_groups", groups)
        return groups.values()

    def get_drivers_table(self):
        driver_list = []
        for group_id in self.get_car_groups():
            response = self.get_target_url(url=f"{self.base_url}group/{group_id}/drivers")
            for driver in response['data']:
                driver_list.append({
                    'fleet_name': self.fleet,
                    'name': driver['full_name'].split()[-2],
                    'second_name': driver['full_name'].split()[-3],
                    'email': None,
                    'phone_number': driver['phone_number'],
                    'driver_external_id': driver['id'],
                    'pay_cash': True,
                    'licence_plate': driver['vehicle_numbers'],
                    'vehicle_name': '',
                    'vin_code': '',
                    'worked': True,
                })
        return driver_list

    def get_vehicles(self):
        vehicles_list = []
        for group_id in self.get_car_groups():
            response = self.get_target_url(url=f"{self.base_url}group/{group_id}/vehicles")
            vehicles = response['data']
            for vehicle in vehicles:
                vehicles_list.append({
                    'licence_plate': vehicle['number'],
                    'vehicle_name': f"{vehicle['brand']} {vehicle['model']}",
                    'vin_code': ''
                })
        return vehicles_list

#
#     def post_target_url(self, url, params, json):
#         new_token = self.get_access_token()
#         headers = {'Authorization': f'Bearer {new_token}'}
#         response = requests.post(url, json=json, params=params, headers=headers)
#         return response.json()
#
    # def save_report(self, day):
    #     reports = Payments.objects.filter(report_from=day, vendor_name=self.fleet, partner=self.partner_id)
    #     if reports:
    #         return list(reports)
    #     # date format str yyyy-mm-dd
    #     format_day = day.strftime("%Y-%m-%d")
    #     param = self.param
    #     param.update({"start_date": format_day,
    #                   "end_date": format_day,
    #                   "offset": 0,
    #                   "limit": 50})
    #     reports = self.get_target_url(f'{self.base_url}getDriverEarnings/dateRange', param)
    #     param['limit'] = 25
    #     rides = self.get_target_url(f'{self.base_url}getDriverEngagementData/dateRange', param)
    #     for driver in reports['data']['drivers']:
    #         order = Payments(
    #             report_from=day,
    #             vendor_name=self.fleet,
    #             full_name=driver['name'],
    #             driver_id=driver['id'],
    #             total_amount_cash=driver['cash_in_hand'],
    #             total_amount=driver['gross_revenue'],
    #             tips=driver['tips'],
    #             partner=Partner.get_partner(self.partner_id),
    #             bonuses=driver['bonuses'],
    #             cancels=driver['cancellation_fees'],
    #             fee=-(driver['gross_revenue'] - driver['net_earnings']),
    #             total_amount_without_fee=driver['net_earnings'],
    #             compensations=driver['compensations'],
    #             refunds=driver['expense_refunds'],
    #         )
    #         for rider in rides['data']['rows']:
    #             if driver['id'] == rider['id']:
    #                 order.total_rides = rider['finished_orders']
    #         try:
    #             order.save()
    #         except IntegrityError:
    #             pass
#

#
#     def get_fleet_orders(self, day, pk):
#         bolt_states = {
#             "client_did_not_show": FleetOrder.CLIENT_CANCEL,
#             "finished": FleetOrder.COMPLETED,
#             "client_cancelled": FleetOrder.CLIENT_CANCEL,
#             "driver_cancelled_after_accept": FleetOrder.DRIVER_CANCEL,
#             "driver_rejected": FleetOrder.DRIVER_CANCEL
#         }
#         driver = Driver.objects.get(pk=pk)
#         driver_id = driver.get_driver_external_id(self.fleet)
#         if driver_id:
#             format_day = day.strftime("%Y-%m-%d")
#             payload = {
#                       "offset": 0,
#                       "limit": 50,
#                       "from_date": format_day,
#                       "to_date": format_day,
#                       "driver_id": driver_id,
#                       "orders_state_statuses": [
#                                                 "client_did_not_show",
#                                                 "finished",
#                                                 "client_cancelled",
#                                                 "driver_cancelled_after_accept",
#                                                 "driver_rejected"
#                                                 ]
#                     }
#             report = self.post_target_url(f'{self.base_url}getOrdersHistory', self.param, payload)
#             time.sleep(0.5)
#             if report.get('data'):
#                 for order in report['data']['rows']:
#                     if FleetOrder.objects.filter(order_id=order['order_id']):
#                         continue
#                     try:
#                         finish = timezone.make_aware(datetime.datetime.fromtimestamp(order['order_stops'][-1]['arrived_at']))
#                     except TypeError:
#                         finish = None
#                     data = {"order_id": order['order_id'],
#                             "fleet": self.fleet,
#                             "driver": driver,
#                             "from_address": order['pickup_address'],
#                             "accepted_time": timezone.make_aware(datetime.datetime.fromtimestamp(order['accepted_time'])),
#                             "state": bolt_states.get(order['order_try_state']),
#                             "finish_time": finish,
#                             "destination": order['order_stops'][-1]['address'],
#                             "partner": Partner.get_partner(self.partner_id)
#                             }
#                     FleetOrder.objects.create(**data)
#
#     def get_drivers_status(self):
#         with_client = []
#         wait = []
#         report = self.get_target_url(f'{self.base_url}getDriversForLiveMap', self.param)
#         if report.get('data'):
#             for driver in report['data']['list']:
#                 name, second_name = driver['name'].split(' ')
#                 if driver['state'] == 'waiting_orders':
#                     wait.append((name, second_name))
#                     wait.append((second_name, name))
#                 else:
#                     with_client.append((name, second_name))
#                     with_client.append((second_name, name))
#         return {'wait': wait,
#                 'with_client': with_client}
#
#     def cash_restriction(self, pk, enable):
#         driver = Driver.objects.get(pk=pk)
#         driver_id = driver.get_driver_external_id(self.fleet)
#         payload = {
#             "driver_id": driver_id,
#             "has_cash_payment": enable
#         }
#         self.post_target_url(f'{self.base_url}driver/toggleCash', self.param, payload)
#         pay_cash = True if enable == 'true' else False
#         Fleets_drivers_vehicles_rate.objects.filter(driver_external_id=driver_id).update(pay_cash=pay_cash)
#
#     def add_driver(self, job_application):
#         headers = {
#             'Content-Type': 'application/x-www-form-urlencoded'
#         }
#         payload = {
#                         "email": f"{job_application.email}",
#                         "phone": f"{job_application.phone_number}",
#                         "referral_code": ""
#                 }
#         response = self.post_target_url(f'{self.base_url}addDriverRegistration', self.param, payload)
#         payload_form = {
#             'hash': response['data']['hash'],
#             'last_step': 'step_2',
#             'first_name': job_application.first_name,
#             'last_name': job_application.last_name,
#             'email': job_application.email,
#             'phone': job_application.phone_number,
#             'birthday': '',
#             'terms_consent_accepted': '0',
#             'whatsapp_opt_in': '0',
#             'city_data': 'Kyiv|ua|uk|634|₴|158',
#             'city_id': '158',
#             'language': 'uk',
#             'referral_code': '',
#             'has_car': '0',
#             'allow_fleet_matching': '',
#             'personal_code': '',
#             'driver_license': '',
#             'has_taxi_license': '0',
#             'type': 'person',
#             'license_type_selection': '',
#             'company_name': '',
#             'address': '',
#             'reg_code': '',
#             'company_is_liable_to_vat': '0',
#             'vat_code': '',
#             'beneficiary_name': '',
#             'iban': '',
#             'swift': '',
#             'account_branch_code': '',
#             'remote_training_url': '',
#             'flow_id': '',
#             'web_marketing_data[fbp]': '',
#             'web_marketing_data[url]': f"{response['data']['registration_link']}/2",
#             'web_marketing_data[user_agent]': '''Mozilla/5.0 (Windows NT 10.0; Win64; x64)
#              AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36''',
#             'is_fleet_company': '1'
#         }
#
#         encoded_payload = parse.urlencode(payload_form)
#         params = {
#             'version': 'DP.11.89',
#             'hash': response['data']['hash'],
#             'language': 'uk-ua',
#         }
#         second_params = dict(list(params.items())[:1])
#         requests.post(f'{BoltService.get_value("R_BOLT_ADD_DRIVER_1")}register/',
#                       params=second_params, headers=headers, data=encoded_payload)
#         requests.get(f"{BoltService.get_value('R_BOLT_ADD_DRIVER_1')}getDriverRegistrationDocumentsSet/", params=params)
#
#         file_paths = [
#             f"{settings.MEDIA_URL}{job_application.driver_license_front}",  # license_front
#             f"{settings.MEDIA_URL}{job_application.photo}",  # photo
#             f"{settings.MEDIA_URL}{job_application.car_documents}",  # car_document
#             f"{settings.MEDIA_URL}{job_application.insurance}"  # insurance
#         ]
#
#         payloads = [
#             {'hash': response['data']['hash'], 'expires': str(job_application.license_expired)},
#             {'hash': response['data']['hash']},
#             {'hash': response['data']['hash']},
#             {'hash': response['data']['hash'], 'expires': str(job_application.insurance_expired)}
#         ]
#
#         file_keys = [
#             'ua_drivers_license',
#             'ua_profile_pic',
#             'ua_technical_passport',
#             'ua_insurance_policy'
#         ]
#
#         for file_path, key, payload in zip(file_paths, file_keys, payloads):
#             files = {}
#             binary = requests.get(file_path).content
#             mime_type, _ = mimetypes.guess_type(file_path)
#             file_name = file_path.split('/')[-1]
#             files[key] = (file_name, binary, mime_type)
#             requests.post(f'{BoltService.get_value("R_BOLT_ADD_DRIVER_1")}uploadDriverRegistrationDocument/',
#                           params=params, data=payload, files=files)
#         payload_form['last_step'] = 'step_4'
#         payload_form['web_marketing_data[url]'] = f"{response['data']['registration_link']}/4"
#         encoded = parse.urlencode(payload_form)
#         requests.post(f'{BoltService.get_value("R_BOLT_ADD_DRIVER_1")}register/', headers=headers,
#                       params=params, data=encoded)
#         job_application.status_bolt = datetime.datetime.now().date()
#         job_application.save()
#
#     def get_vehicles(self):
#         vehicles_list = []
#         start = end = pendulum.now().strftime('%Y-%m-%d')
#         params = {"start_date": start,
#                   "end_date": end,
#                   "offset": 0,
#                   "limit": 25}
#         params.update(self.param)
#         response = self.get_target_url(f'{self.base_url}getCarsPaginated', params=params)
#         vehicles = response['data']['rows']
#         for vehicle in vehicles:
#             vehicles_list.append({
#                 'licence_plate': vehicle['reg_number'],
#                 'vehicle_name': vehicle['model'],
#                 'vin_code': ''
#             })
#         return vehicles_list
