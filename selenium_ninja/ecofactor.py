from datetime import datetime, timedelta

import pytz
import requests
from django.db import transaction
from django.utils import timezone

from app.models import Driver, Penalty, Category, ParkSettings, ChargeTransactions
from auto_bot.handlers.order.utils import check_vehicle
from scripts.redis_conn import redis_instance
from selenium_ninja.driver import SeleniumTools


class EcoFactorRequest:
    url = "https://operator.ecofactor.eu/graphql"

    @staticmethod
    def create_session():
        SeleniumTools().get_ecofactor_token()

    @staticmethod
    def get_header():
        token = redis_instance().get("eco_token")
        headers = {'Authorization': f'Bearer {token}'}
        return headers

    @staticmethod
    def get_payload(query, variables):
        data = {
            'query': query,
            'variables': variables
        }
        return data

    def get_driver_transactions(self, start, end):
        query = """query (
                      $partnerPk1: Float
                      $chargePointPk2: Float
                      $connectorType3: String
                      $connectorPk4: Float
                      $partnerClientGroupPk5: Float
                      $clientPk6: Float
                      $status7: ChargingStatus
                      $from8: DateTime
                      $to9: DateTime
                      $search10: String
                      $skip11: Int
                      $take12: Int
                      $pk13: Float!
                    ) {
                      chargings_b17e0_6b4e2: chargings(
                        partnerPk: $partnerPk1
                        chargePointPk: $chargePointPk2
                        connectorType: $connectorType3
                        connectorPk: $connectorPk4
                        partnerClientGroupPk: $partnerClientGroupPk5
                        clientPk: $clientPk6
                        status: $status7
                        from: $from8
                        to: $to9
                        search: $search10
                        skip: $skip11
                        take: $take12
                      ) {
                        __typename
                        rows {
                          status
                          clientInfo {
                            clientName
                          }
                          
                          created
                          duration
                          pk
                          charged
                        }
                        total {
                          __typename
                          count
                        }
                      }
                      partner_95e0e_6f0b9: partner(pk: $pk13) {
                        __typename
                        currency {
                          __typename
                          symbol
                        }
                      }
                    }"""

        variables = {
              "partnerPk1": 430,
              "chargePointPk2": None,
              "connectorType3": None,
              "connectorPk4": None,
              "partnerClientGroupPk5": None,
              "clientPk6": None,
              "status7": "complete",
              "from8": start.isoformat(),
              "to9": end.isoformat(),
              "search10": None,
              "skip11": 0,
              "take12": 50,
              "pk13": 430
            }
        data = self.get_payload(query, variables)
        response = requests.post(self.url, headers=self.get_header(), json=data)
        if response.json().get('errors'):
            self.create_session()
            response = requests.post(self.url, headers=self.get_header(), json=data)
        response_data = response.json()['data']['chargings_b17e0_6b4e2']['rows']
        existing_charging = ChargeTransactions.objects.filter(
            start_time__range=(start, end)).values_list('charge_id', flat=True)
        new_charges = [entry for entry in response_data if entry['pk'] not in existing_charging]
        batch_data = []
        for entry in new_charges:
            client_name = entry['clientInfo']['clientName']
            second_name, name = client_name.split()
            driver = Driver.objects.get_active(second_name=second_name, name=name).first()
            start = timezone.make_aware(datetime.strptime(entry['created'], '%Y-%m-%dT%H:%M:%S.%fZ'),
                                        timezone=timezone.utc)
            start_time = timezone.localtime(start)
            vehicle = check_vehicle(driver, start_time)

            data = {
                "charge_id": entry['pk'],
                "start_time": start_time,
                "end_time": start_time + timedelta(seconds=entry['duration']),
                "charge_amount": entry['charged'] / 1000,
                "driver": driver,
                "vehicle": vehicle,
                "price": ParkSettings.get_value("CHARGE_PRICE", partner=driver.partner if driver else 1, default=8)
            }
            charge_transaction = ChargeTransactions(**data)
            batch_data.append(charge_transaction)
        with transaction.atomic():
            ChargeTransactions.objects.bulk_create(batch_data)