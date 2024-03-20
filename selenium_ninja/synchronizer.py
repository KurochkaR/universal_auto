from io import BytesIO

import requests
from django.core.exceptions import ObjectDoesNotExist
from django.core.files import File
from django.db.models import Q

from app.models import Fleet, FleetsDriversVehiclesRate, Driver, Vehicle, Role, JobApplication, ParkSettings, Manager, \
    Schema
from auto_bot.handlers.order.utils import normalized_plate
from auto_bot.main import bot


class AuthenticationError(Exception):
    def __init__(self, message="Authentication error"):
        self.message = message
        super().__init__(self.message)


class InfinityTokenError(Exception):
    def __init__(self, message="No infinity gps token"):
        self.message = message
        super().__init__(self.message)


class Synchronizer:

    def get_drivers_table(self):
        raise NotImplementedError

    def get_vehicles(self):
        raise NotImplementedError

    def synchronize(self):
        drivers = self.get_drivers_table()
        vehicles = self.get_vehicles()
        for vehicle in vehicles:
            self.get_or_create_vehicle(**vehicle)
        for driver in drivers:
            self.create_driver(**driver)
        print(f'Finished {self} drivers: {len(drivers)}')

    def create_driver(self, **kwargs):
        driver = FleetsDriversVehiclesRate.objects.filter(fleet=self,
                                                          driver_external_id=kwargs['driver_external_id'],
                                                          partner=self.partner).first()
        if not driver:
            FleetsDriversVehiclesRate.objects.create(fleet=self,
                                                     driver_external_id=kwargs['driver_external_id'],
                                                     driver=self.get_or_create_driver(**kwargs),
                                                     partner=self.partner)
        else:
            if kwargs.get('pay_cash') is not None and driver.pay_cash != kwargs.get('pay_cash'):
                driver.pay_cash = kwargs.get('pay_cash')
                driver.save(update_fields=['pay_cash'])
                bot.send_message(chat_id=ParkSettings.get_value("DEVELOPER_CHAT_ID"),
                                 text=f"{driver.fleet} {driver.driver} оновлено поле оплата готівкою")
            self.update_driver_fields(driver.driver, **kwargs)

    def get_or_create_driver(self, **kwargs):
        driver = Driver.objects.filter((Q(name=kwargs['name'], second_name=kwargs['second_name']) |
                                        Q(name=kwargs['second_name'], second_name=kwargs['name']) |
                                        Q(phone_number__icontains=kwargs['phone_number'][-10:])
                                        ) & Q(partner=self.partner.id)).first()

        if not driver and kwargs['email']:
            driver = Driver.objects.filter(email__icontains=kwargs['email']).first()
        if not driver:
            data = {"name": kwargs['name'],
                    "second_name": kwargs['second_name'],
                    "role": Role.DRIVER,
                    "partner": self.partner
                    }
            if self.partner.contacts:
                phone_number = kwargs['phone_number'] if len(kwargs['phone_number']) <= 13 else None
                data.update({"phone_number": phone_number,
                             "email": kwargs['email']
                             })
            managers = Manager.objects.filter(managers_partner=self.partner)
            schema = Schema.objects.filter(managers_partner=self.partner)

            manager_msg = f" з {managers.count()} менеджерами" if managers.count() > 1 else ""
            schema_msg = f" з {schema.count()} схемами" if schema.count() > 1 else ""

            if managers.count() == 1:
                data['manager'] = managers.first()
                if schema.count() == 1:
                    data['schema'] = schema.first()
                elif schema.count() > 1:
                    bot.send_message(chat_id=managers.first().chat_id,
                                     text=f"У вас новий водій: {kwargs['name']} {kwargs['second_name']} без вказаної схеми{manager_msg}. Потрібно вибрати одну схему.")
                else:
                    bot.send_message(chat_id=managers.first().chat_id,
                                     text=f"У вас новий водій: {kwargs['name']} {kwargs['second_name']} без вказаної схеми{manager_msg}. Потрібно додати та призначити схему.")

            elif managers.count() > 1:
                bot.send_message(chat_id=ParkSettings.get_value("DEVELOPER_CHAT_ID"),
                                 text=f"У вас новий водій: {kwargs['name']} {kwargs['second_name']} із не вказаним менеджером{schema_msg}")
            else:
                bot.send_message(chat_id=ParkSettings.get_value("DEVELOPER_CHAT_ID"),
                                 text=f"У вас новий водій: {kwargs['name']} {kwargs['second_name']}. Не знайдено жодного менеджера.")

            driver = Driver.objects.create(**data)
            try:
                client = JobApplication.objects.get(first_name=kwargs['name'], last_name=kwargs['second_name'])
                driver.chat_id = client.chat_id
                driver.save()
                fleet = Fleet.objects.get(name='Ninja')
                FleetsDriversVehiclesRate.objects.get_or_create(
                    fleet=fleet,
                    driver_external_id=driver.chat_id,
                    driver=driver,
                    partner=self.partner
                )
            except ObjectDoesNotExist:
                pass
        else:
            self.update_driver_fields(driver, **kwargs)
        return driver

    def get_or_create_vehicle(self, **kwargs):
        licence_plate, v_name, vin = kwargs['licence_plate'], kwargs['vehicle_name'], kwargs['vin_code']
        if licence_plate:
            plate = normalized_plate(licence_plate)
            vehicle, created = Vehicle.objects.get_or_create(licence_plate=plate,
                                                             defaults={
                                                                 "name": v_name.upper(),
                                                                 "licence_plate": plate,
                                                                 "vin_code": vin,
                                                                 "partner": self.partner
                                                             })
            if not created:
                self.update_vehicle_fields(vehicle, **kwargs)
            return vehicle

    def update_vehicle_fields(self, vehicle, **kwargs):
        vehicle_name = kwargs.get('vehicle_name')
        vin_code = kwargs.get('vin_code')
        if vehicle_name and vehicle.name != vehicle_name:
            vehicle.name = vehicle_name

        if vin_code and vehicle.vin_code != vin_code:
            vehicle.vin_code = vin_code

        vehicle.partner = self.partner
        vehicle.save(update_fields=['name', 'vin_code', 'partner'])

    def update_driver_fields(self, driver, **kwargs):
        phone_number = kwargs.get('phone_number')
        photo = kwargs.get('photo')
        email = kwargs.get('email')

        if photo and "default.jpeg" not in photo and 'drivers/default-driver.png' == driver.photo:
            response = requests.get(photo)
            if response.status_code == 200:
                image_data = response.content
                image_file = BytesIO(image_data)
                driver.photo = File(image_file, name=f"{driver.name}_{driver.second_name}.jpg")
        if driver.partner.contacts:
            if phone_number and not driver.phone_number:
                driver.phone_number = phone_number
            if email and driver.email != email:
                driver.email = email
        driver.save(update_fields=['phone_number', 'photo', 'email'])

    @staticmethod
    def report_interval(date_time):
        return int(date_time.timestamp())
