import requests

from app.models import UberService, Payments, UberSession, Fleets_drivers_vehicles_rate, Partner, FleetOrder
from auto_bot.handlers.order.utils import check_vehicle
from selenium_ninja.driver import SeleniumTools

from selenium_ninja.synchronizer import Synchronizer


class UberRequest(Synchronizer):

    def __init__(self, partner_id=None, fleet="Uber"):
        super().__init__(partner_id, fleet)
        self.base_url = UberService.get_value('REQUEST_UBER_BASE_URL')

    def get_header(self):
        obj_session = UberSession.objects.filter(partner=self.partner_id).latest('created_at')
        headers = {
            "content-type": "application/json",
            "x-csrf-token": "x",
            "cookie": f"sid={obj_session.session}; csid={obj_session.cook_session}"
        }
        return headers

    def get_uuid(self):
        obj_session = UberSession.objects.filter(partner=self.partner_id).latest('created_at')
        return str(obj_session.uber_uuid)

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
        response = requests.post(self.base_url, headers=self.get_header(), json=data)
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
            drivers.append({'fleet_name': self.fleet,
                            'name': self.remove_dup(driver['member']['user']['name']['firstName']),
                            'second_name': self.remove_dup(driver['member']['user']['name']['lastName']),
                            'email': driver['member']['user']['email'],
                            'phone_number': phone['countryCode'] + phone['nationalPhoneNumber'],
                            'driver_external_id': driver['member']['user']['uuid'],
                            'licence_plate': licence_plate,
                            'pay_cash': True,
                            'vehicle_name': vehicle_name,
                            'vin_code': vin_code,
                            'worked': True})
        return drivers

    def save_report(self, start, end):
        format_start = self.report_interval(start) * 1000
        format_end = self.report_interval(end) * 1000
        uber_drivers = Fleets_drivers_vehicles_rate.objects.filter(partner=self.partner_id,
                                                                   fleet__name=self.fleet)
        drivers_id = [obj.driver_external_id for obj in uber_drivers]
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
                            "expressions": drivers_id
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
        if uber_drivers:
            db_driver = Fleets_drivers_vehicles_rate.objects.get(driver_external_id=drivers_id,
                                                                 partner=self.partner_id).driver
            if db_driver.schema.pay_time == start.time():
                data = self.get_payload(query, variables)
                response = requests.post(self.base_url, headers=self.get_header(), json=data)
                if response.status_code == 200 and response.json()['data']:
                    for report in response.json()['data']['getPerformanceReport']:
                        if report['totalEarnings']:
                            driver = Fleets_drivers_vehicles_rate.objects.get(driver_external_id=report['uuid'],
                                                                              partner=self.partner_id).driver
                            vehicle = check_vehicle(driver, end, max_time=True)[0]
                            report = {
                                "report_from": start,
                                "report_to": end,
                                "vendor_name": self.fleet,
                                "driver_id": report['uuid'],
                                "full_name": str(driver),
                                "total_amount": round(report['totalEarnings'], 2),
                                "total_amount_without_fee": round(report['totalEarnings'], 2),
                                "total_amount_cash": round(report['cashEarnings'], 2),
                                "total_rides": report['totalTrips'],
                                "partner": Partner.get_partner(self.partner_id),
                                "vehicle": vehicle
                            }
                            db_report = Payments.objects.filter(report_from=start,
                                                                driver_id=report['uuid'],
                                                                vendor_name=self.fleet,
                                                                partner=self.partner_id)
                            db_report.update(**report) if db_report else Payments.objects.create(**report)
                else:
                    self.logger.error(f"Failed save uber report {self.partner_id} {response}")

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
        response = requests.post(self.base_url, headers=self.get_header(), json=data)
        if response.status_code == 200:
            drivers = response.json()['data']['getDriverEvents']['driverEvents']
            if drivers:
                for rider in drivers:
                    rate = Fleets_drivers_vehicles_rate.objects.filter(driver_external_id=rider['driverUUID']).first()
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
        response = requests.post(self.base_url, headers=self.get_header(), json=data)
        if response.status_code == 200:
            vehicles_list = []
            vehicles = response.json()["data"]["getSupplierVehicles"]["vehicles"]
            for vehicle in vehicles:
                vehicles_list.append({
                    'licence_plate': vehicle['licensePlate'],
                    'vehicle_name': f'{vehicle["make"]} {vehicle["model"]}',
                    'vin_code': vehicle['vin']})
            return vehicles_list

    def get_fleet_orders(self, day):
        if not FleetOrder.objects.filter(fleet="Uber", accepted_time__date=day):
            uber_driver = SeleniumTools(self.partner_id)
            uber_driver.download_payments_order("Uber", day)
            uber_driver.save_trips_report("Uber", day)
            uber_driver.quit()
