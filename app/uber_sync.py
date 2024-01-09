from datetime import datetime
import requests
from django.db import models
from app.models import UberService, UberSession, FleetsDriversVehiclesRate, FleetOrder, \
    CustomReport, Fleet, CredentialPartner, WeeklyReport, DailyReport
from auto_bot.handlers.order.utils import check_vehicle
from scripts.redis_conn import get_logger
from selenium_ninja.driver import SeleniumTools
from selenium_ninja.synchronizer import Synchronizer


class UberRequest(Fleet, Synchronizer):
    base_url = models.URLField(default=UberService.get_value('REQUEST_UBER_BASE_URL'))

    def get_header(self):
        obj_session = UberSession.objects.filter(partner=self.partner).latest('created_at')
        headers = {
            "content-type": "application/json",
            "x-csrf-token": "x",
            "cookie": f"sid={obj_session.session}; csid={obj_session.cook_session}"
        }
        return headers

    def get_uuid(self):
        obj_session = UberSession.objects.filter(partner=self.partner).latest('created_at')
        return str(obj_session.uber_uuid)

    @staticmethod
    def create_session(partner, login, password):
        if not login:
            login = CredentialPartner.get_value(key='UBER_NAME', partner=partner)
            password = CredentialPartner.get_value(key='UBER_PASSWORD', partner=partner)
        if login and password:
            SeleniumTools(partner).create_uber_session(login, password)

    @staticmethod
    def remove_dup(text):
        if 'DUP' in text:
            text = text[:-3]
        return text

    @staticmethod
    def get_payload(query, variables):
        data = {
            'query': query,
            'variables': variables
        }
        return data

    def get_drivers_table(self):
        query = '''
          query GetDrivers(
            $orgUUID: ID!,
            $pagingOptions: PagingOptionsInput!,
            $filters: GetDriversFiltersInput
          ) {
            getDrivers(
              orgUUID: $orgUUID,
              pagingOptions: $pagingOptions,
              filters: $filters
            ) {
              orgUUID
              drivers {
                ...DriversTableRowFields
              }
              pagingResult {
                nextPageToken
              }
            }
          }

          fragment DriversTableRowFields on Driver {
            member {
              user {
                uuid
                name {
                  firstName
                  lastName
                }
                pictureUrl
                email
                phone {
                  countryCode
                  nationalPhoneNumber
                }
              }
            }
            associatedVehicles {
              uuid
              make
              model
              vin
              year
              licensePlate
            }
          }
        '''
        variables = {
                    "orgUUID": self.get_uuid(),
                    "pagingOptions": {
                        "pageSize": 25
                                    },
                    "filters": {
                                "complianceStatuses": [],
                                "vehicleAssignmentStatuses": [],
                                "documentStatuses": []
                                }
                    }
        drivers = []
        data = self.get_payload(query, variables)
        response = requests.post(str(self.base_url), headers=self.get_header(), json=data)
        if response.status_code in (502, 504):
            return drivers
        drivers_data = response.json()['data']['getDrivers']['drivers']
        for driver in drivers_data:
            licence_plate = ''
            vehicle_name = ''
            vin_code = ''
            if driver['associatedVehicles']:
                licence_plate = driver['associatedVehicles'][0]['licensePlate']
                vehicle_name = driver['associatedVehicles'][0]['make']
                vin_code = driver['associatedVehicles'][0]['vin']
            phone = driver['member']['user']['phone']
            drivers.append({'fleet_name': self.name,
                            'name': self.remove_dup(driver['member']['user']['name']['firstName']),
                            'second_name': self.remove_dup(driver['member']['user']['name']['lastName']),
                            'email': driver['member']['user']['email'],
                            'phone_number': phone['countryCode'] + phone['nationalPhoneNumber'],
                            'driver_external_id': driver['member']['user']['uuid'],
                            'licence_plate': licence_plate,
                            'pay_cash': True,
                            'photo': driver['member']['user']['pictureUrl'],
                            'vehicle_name': vehicle_name,
                            'vin_code': vin_code,
                            })
        return drivers

    def generate_report(self, start, end, driver):
        format_start = self.report_interval(start) * 1000
        format_end = self.report_interval(end) * 1000
        driver_id = driver.get_driver_external_id(self.name)
        if format_start >= format_end or not driver_id:
            return
        query = '''query GetPerformanceReport($performanceReportRequest: PerformanceReportRequest__Input!) {
                  getPerformanceReport(performanceReportRequest: $performanceReportRequest) {
                    uuid
                    totalEarnings
                    totalTrips
                    ... on DriverPerformanceDetail {
                      cashEarnings
                    }
                  }
                }'''
        variables = {
                      "performanceReportRequest": {
                        "orgUUID": self.get_uuid(),
                        "dimensions": [
                          "vs:driver"
                        ],
                        "dimensionFilterClause": [
                          {
                            "dimensionName": "vs:driver",
                            "operator": "OPERATOR_IN",
                            "expressions": driver_id
                          }
                        ],
                        "metrics": [
                          "vs:TotalEarnings",
                          "vs:TotalTrips",
                          "vs:CashEarnings",
                          "vs:DriverAcceptanceRate"
                        ],
                        "timeRange": {
                          "startsAt": {
                            "value": format_start
                          },
                          "endsAt": {
                            "value": format_end
                          }
                        }
                      }
                    }
        data = self.get_payload(query, variables)
        response = requests.post(str(self.base_url), headers=self.get_header(), json=data)
        if response.status_code == 200 and response.json()['data']:
            result = response.json()['data']['getPerformanceReport']
        else:
            get_logger().error(f"Failed save uber report {self.partner} {response.json()}")
            result = []
        return result

    def parse_json_report(self, start, end, driver, report):
        vehicle = check_vehicle(driver, end, max_time=True)
        payment = {
            "report_from": start,
            "report_to": end,
            "vendor": self,
            "driver": driver,
            "total_amount": round(report['totalEarnings'], 2),
            "total_amount_without_fee": round(report['totalEarnings'], 2),
            "total_amount_cash": round(report['cashEarnings'], 2),
            "total_rides": report['totalTrips'],
            "partner": self.partner,
            "vehicle": vehicle
        }
        return payment

    def custom_saving_report(self, start, end, driver, model):
        reports = self.generate_report(start, end, driver)
        if reports:
            for report in reports:
                if report['totalEarnings']:
                    payment = self.parse_json_report(start, end, driver, report)
                    db_report, created = model.objects.get_or_create(report_from=start,
                                                                     driver=driver,
                                                                     vendor=self,
                                                                     partner=self.partner,
                                                                     defaults=payment)
                    if not created:
                        for key, value in payment.items():
                            setattr(db_report, key, value)
                        db_report.save()
                    return db_report

    def save_custom_report(self, start, end, driver):
        return self.custom_saving_report(start, end, driver, CustomReport)

    def save_weekly_report(self, start, end, driver):
        return self.custom_saving_report(start, end, driver, WeeklyReport)

    def save_daily_report(self, start, end, driver):
        return self.custom_saving_report(start, end, driver, DailyReport)

    def get_earnings_per_driver(self, driver, start_time, end_time):
        report = self.generate_report(start_time, end_time, driver)
        if report:
            return report[0]['totalEarnings'], report[0]['cashEarnings']
        else:
            return 0, 0

    def get_drivers_status(self):
        query = '''query GetDriverEvents($orgUUID: String!) {
                      getDriverEvents(orgUUID: $orgUUID) {
                        driverEvents {
                          driverUUID
                          driverStatus
                        }
                      }
                    }'''
        variables = {
                    "orgUUID": self.get_uuid()
                     }
        with_client = []
        wait = []
        data = self.get_payload(query, variables)
        response = requests.post(str(self.base_url), headers=self.get_header(), json=data)
        if response.status_code == 200:
            drivers = response.json()['data']['getDriverEvents']['driverEvents']
            if drivers:
                for rider in drivers:
                    rate = FleetsDriversVehiclesRate.objects.filter(driver_external_id=rider['driverUUID']).first()
                    if rate:
                        name, second_name = rate.driver.name, rate.driver.second_name
                        if rider["driverStatus"] == "online":
                            wait.append((name, second_name))
                            wait.append((second_name, name))
                        elif rider["driverStatus"] in ("accepted", "in_progress"):
                            with_client.append((name, second_name))
                            with_client.append((second_name, name))
        return {'wait': wait,
                'with_client': with_client}

    def get_vehicles(self):
        query = '''query vehiclesTableVehicles($orgUUID: String, $pageSize: Int) {
                      getSupplierVehicles(
                        orgUUID: $orgUUID
                        pageSize: $pageSize
                      ) {
                        vehicles {
                          ...VehicleDetailsFields
                        }
                      }
                    }
                    fragment VehicleDetailsFields on Vehicle {
                      make
                      model
                      licensePlate
                      vin
                    }'''
        variables = {
            "orgUUID": self.get_uuid(),
            "pageSize": 25
        }
        data = self.get_payload(query, variables)
        response = requests.post(str(self.base_url), headers=self.get_header(), json=data)
        if response.status_code == 200:
            vehicles_list = []
            vehicles = response.json()["data"]["getSupplierVehicles"]["vehicles"]
            for vehicle in vehicles:
                vehicles_list.append({
                    'licence_plate': vehicle['licensePlate'],
                    'vehicle_name': f'{vehicle["make"]} {vehicle["model"]}',
                    'vin_code': vehicle['vin']})
            return vehicles_list

    def get_fleet_orders(self, start, end):
        if not FleetOrder.objects.filter(fleet="Uber", accepted_time__range=(start, end)).exists():
            uber_driver = SeleniumTools(self.partner.id)
            uber_driver.download_payments_order(start, end)
            uber_driver.save_trips_report(start, end)
            uber_driver.quit()

    def disable_cash(self, driver_id, enable):
        date = datetime.now()
        period = date.isoformat() + "Z"
        block_query = '''mutation EnableCashBlocks($supplierUuid: UberDataSchemasBasicProtoUuidInput!,
         $earnerUuid: UberDataSchemasBasicProtoUuidInput!) {
                    enableCashBlock(
                        supplierUuid: $supplierUuid
                        earnerUuid: $earnerUuid
                      ) { 
                      cashBlockOverride {
                        earnerUuid {
                        value
                        __typename
                        }
                      }
                      __typename
                    }
        }'''
        unblock_query = '''mutation DisableCashBlocks(
                            $supplierUuid: UberDataSchemasBasicProtoUuidInput!,
                             $earnerUuid: UberDataSchemasBasicProtoUuidInput!,
                              $effectiveAt: UberDataSchemasTimeProtoDateTimeInput!) {
                              disableCashBlock(
                                supplierUuid: $supplierUuid
                                earnerUuid: $earnerUuid
                                effectiveAt: $effectiveAt
                              ) {
                                cashBlockOverride {
                                  earnerUuid {
                                    value
                                    __typename
                                  }
                                }
                                __typename
                              }
                            }'''
        variables = {
                    "supplierUuid": {"value": self.get_uuid()},
                    "earnerUuid": {"value": driver_id},
                    "effectiveAt": {"value": period}
        }
        query = unblock_query if enable else block_query
        data = self.get_payload(query, variables)
        requests.post(str(self.base_url), headers=self.get_header(), json=data)
