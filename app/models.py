import os
import string
import random
from datetime import datetime, date, time
from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.validators import MaxLengthValidator, EmailValidator, RegexValidator, MinValueValidator, \
    MaxValueValidator
from django.db.models import Sum, F, Q
from django.db.models.signals import post_delete
from django.utils import timezone
from django.db import models, ProgrammingError
from django.utils.safestring import mark_safe
from polymorphic.models import PolymorphicModel
from django.contrib.auth.models import AbstractUser
from cryptography.fernet import Fernet


class SoftDeleteManager(models.Manager):
    def delete(self):
        deleted_items = self.get_queryset()
        deleted_items.update(deleted_at=timezone.localtime())
        for item in deleted_items:
            post_delete.send(sender=item.__class__, instance=item)
        return len(deleted_items)

    def get_active(self, **kwargs):
        return self.get_queryset().filter(**kwargs, deleted_at__isnull=True)


class InvestorSchema(models.TextChoices):
    Equal_share = 'Equal_share', 'Рівномірна',
    Proportional = 'Proportional', 'Пропорційна',
    Rental = 'Rental', 'Оренда'


class Role(models.TextChoices):
    CLIENT = 'CLIENT', 'Клієнт'
    DRIVER = 'DRIVER', 'Водій'
    DRIVER_MANAGER = 'DRIVER_MANAGER', 'Менеджер водіїв'
    SERVICE_STATION_MANAGER = 'SERVICE_STATION_MANAGER', 'Сервісний менеджер'
    SUPPORT_MANAGER = 'SUPPORT_MANAGER', 'Менеджер підтримки'
    PARTNER = 'PARTNER', 'Власник'
    INVESTOR = 'INVESTOR', 'Інвестор'


class CustomUser(AbstractUser):
    chat_id = models.CharField(blank=True, max_length=10, verbose_name='Ідентифікатор чата')
    # phone_number = models.CharField(max_length=13, blank=True, null=True, verbose_name='Номер телефона')
    role = models.CharField(max_length=25, default=Role.CLIENT, choices=Role.choices)

    def is_partner(self):
        return self.role == Role.PARTNER

    def is_manager(self):
        return self.role == Role.DRIVER_MANAGER

    def is_investor(self):
        return self.role == Role.INVESTOR

    @classmethod
    def get_by_chat_id(cls, chat_id):
        try:
            return cls.objects.get(chat_id=chat_id)
        except ObjectDoesNotExist:
            return None

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class SalaryCalculation(models.TextChoices):
    MONTH = 'MONTH', 'Місяць'
    WEEK = 'WEEK', 'Тиждень'
    DAY = 'DAY', 'День'


class ShiftTypes(models.TextChoices):
    ONE = 'one', 'Один день'
    TWO = 'two', 'Два дні'
    THREE = 'three', 'Три дні'


class PaymentTypes(models.TextChoices):
    CASH = 'cash', 'Готівка'
    CARD = 'card', 'Картка'

    @classmethod
    def map_payments(cls, payment):
        payment_type_mapping = {
            'app_payment': cls.CARD,
            'apple': cls.CARD,
            'google': cls.CARD,
            'card': cls.CARD,
            'cash': cls.CASH,
            'corporatewallet': cls.CARD,
        }

        return payment_type_mapping.get(payment, cls.CARD)


class TaskScheduler(models.Model):
    name = models.CharField(max_length=75, verbose_name="Назва задачі")
    task_time = models.TimeField(verbose_name="Час запуску задачі")
    periodic = models.BooleanField(verbose_name="Періодичний запуск")
    weekly = models.BooleanField(verbose_name="Тижнева задача")
    interval = models.IntegerField(blank=True, null=True, verbose_name="Інтервал запуску")
    arguments = models.IntegerField(null=True, blank=True, verbose_name="Аргументи")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Розклад задач'
        verbose_name_plural = 'Розклад задач'


class Partner(CustomUser):
    gps_url = models.URLField(null=True, verbose_name='Сторінка логіну Gps')
    calendar = models.CharField(max_length=255, verbose_name='Календар змін водіїв')
    contacts = models.BooleanField(default=False, verbose_name='Доступ до контактів')

    class Meta:
        verbose_name = 'Власника'
        verbose_name_plural = 'Власники'


class Category(PolymorphicModel):
    title = models.CharField(max_length=255, null=True, verbose_name='Назва категорії')

    partner = models.ForeignKey(Partner, null=True, on_delete=models.CASCADE, verbose_name='Партнер')

    def __str__(self):
        return self.title

    class Meta:
        unique_together = ['title', 'partner']


class SpendingCategory(Category):
    pass
    # class Meta:
    #     verbose_name = 'Категорія витрат'
    #     verbose_name_plural = 'Категорії витрат'


class PenaltyCategory(Category):
    pass

    class Meta:
        verbose_name = "Категорія штрафу"
        verbose_name_plural = "Категорії штрафів"


class BonusCategory(Category):
    pass

    class Meta:
        verbose_name = "Категорія бонусу"
        verbose_name_plural = "Категорії бонусів"


class Schema(models.Model):
    SCHEMA_CHOICES = [
        ('RENT', 'Схема оренди'),
        ('HALF', 'Схема 50/50'),
        ('DYNAMIC', 'Динамічна схема'),
        ('CUSTOM', 'Індивідуальний відсоток'),
        ('FLOAT', 'Плаваючий відсоток'),
    ]

    title = models.CharField(max_length=255, verbose_name='Назва схеми')
    schema = models.CharField(max_length=25, default=SCHEMA_CHOICES[1],
                              choices=SCHEMA_CHOICES, verbose_name='Шаблон схеми')
    plan = models.IntegerField(default=12000, verbose_name='План водія')
    cash = models.IntegerField(default=500, verbose_name='Контроль готівки водія з, грн')
    rental = models.IntegerField(default=6000, verbose_name='Вартість прокату')
    rate = models.DecimalField(decimal_places=2, max_digits=3, default=0.5, verbose_name='Відсоток водія')
    rent_price = models.IntegerField(default=6, verbose_name='Вартість холостого пробігу')
    limit_distance = models.IntegerField(default=400, verbose_name='Ліміт пробігу за період')
    salary_calculation = models.CharField(max_length=25, choices=SalaryCalculation.choices,
                                          default=SalaryCalculation.WEEK, verbose_name='Період розрахунку зарплати')
    shift_time = models.TimeField(default=time.min, verbose_name="Час проведення розрахунку")
    shift_period = models.CharField(max_length=25, null=True, choices=ShiftTypes.choices)

    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Партнер')

    def __str__(self):
        return self.title if self.title else ''

    def is_weekly(self):
        return True if self.salary_calculation == SalaryCalculation.WEEK else False

    def is_rent(self):
        return True if self.schema == "RENT" else False

    def is_dynamic(self):
        return True if self.schema == "DYNAMIC" else False

    def is_float(self):
        return True if self.schema == "FLOAT" else False

    @classmethod
    def get_weekly_drivers(cls, partner):
        return cls.objects.filter(salary_calculation=SalaryCalculation.WEEK,
                                  partner=partner).values_list('driver', flat=True)

    class Meta:
        verbose_name = 'Схему роботи'
        verbose_name_plural = 'Схеми роботи'


class UberTrips(models.Model):
    report_from = models.DateField(verbose_name="Дата поїздки")
    driver_external_id = models.CharField(max_length=50)
    license_plate = models.CharField(max_length=10)
    start_trip = models.DateTimeField(null=True, blank=True)
    end_trip = models.DateTimeField(null=True, blank=True)

    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Партнер')
    created_at = models.DateTimeField(auto_now_add=True)


class User(models.Model):
    name = models.CharField(validators=[MaxLengthValidator(255)], max_length=255,
                            blank=True, null=True, verbose_name="Ім'я")
    second_name = models.CharField(validators=[MaxLengthValidator(255)], max_length=255,
                                   blank=True, null=True, verbose_name='Прізвище')
    email = models.EmailField(blank=True, null=True, max_length=254, verbose_name='Електронна пошта',
                              validators=[EmailValidator()])
    role = models.CharField(max_length=25, default=Role.CLIENT, choices=Role.choices)
    phone_number = models.CharField(blank=True, null=True, max_length=13, verbose_name='Номер телефона',
                                    validators=[RegexValidator(r"^(\+380|380|80|0)+\d{9}$")])
    chat_id = models.CharField(blank=True, max_length=10, verbose_name='Ідентифікатор чата')
    created_at = models.DateTimeField(editable=False, auto_now_add=True, verbose_name='Створено')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Оновлено')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='Видалено')

    objects = SoftDeleteManager()

    class Meta:
        verbose_name = 'Користувача'
        verbose_name_plural = 'Користувачі'

    def __str__(self) -> str:
        return self.full_name()

    def full_name(self):
        return f'{self.second_name} {self.name}'

    @classmethod
    def get_by_chat_id(cls, chat_id):
        """
        Returns user by chat_id
        :param chat_id: chat_id by which we need to find the user
        :type chat_id: str
        :return: user object or None if a user with such ID does not exist
        """
        try:
            user = cls.objects.get(chat_id=chat_id)
            return user
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def fill_deleted_at_by_number(number):
        """
        :param number: a number of a user to fill deleted_at
        :type number: str
        """
        user = User.objects.filter(phone_number=number).first()
        user.deleted_at = timezone.localtime()
        user.save()
        return user


class Manager(CustomUser):
    managers_partner = models.ForeignKey(Partner, null=True, on_delete=models.CASCADE, verbose_name='Партнер')

    class Meta:
        verbose_name = 'Менеджера'
        verbose_name_plural = 'Менеджери'


class Investor(CustomUser):
    payment_type = models.CharField(max_length=25, choices=SalaryCalculation.choices,
                                          default=SalaryCalculation.WEEK, verbose_name='Періодичність платежів')
    investors_partner = models.ForeignKey(Partner, null=True, on_delete=models.CASCADE, verbose_name='Партнер')

    @classmethod
    def filter_by_weekly_payment(cls, partner):
        return cls.objects.filter(payment_type=SalaryCalculation.WEEK, investors_partner=partner)

    @classmethod
    def filter_by_monthly_payment(cls, partner):
        return cls.objects.filter(payment_type=SalaryCalculation.MONTH, investors_partner=partner)



    class Meta:
        verbose_name = 'Інвестора'
        verbose_name_plural = 'Інвестори'


class GPSNumber(models.Model):
    name = models.CharField(max_length=255, verbose_name='Назва')
    gps_id = models.IntegerField(default=0)

    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Партнер')

    def __str__(self) -> str:
        return f'{self.name}'


class Fleet(PolymorphicModel):
    name = models.CharField(max_length=255)
    fees = models.DecimalField(decimal_places=2, max_digits=3, default=0)
    created_at = models.DateTimeField(editable=False, auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    min_fee = models.DecimalField(decimal_places=2, max_digits=15, default=0)

    partner = models.ForeignKey(Partner, null=True, on_delete=models.CASCADE, verbose_name='Партнери')

    class Meta:
        verbose_name = 'Автопарк'
        verbose_name_plural = 'Автопарки'

    def __str__(self) -> str:
        return f'{self.name} {self.partner}' if self.partner else f'{self.name}'


class Vehicle(models.Model):
    class Currency(models.TextChoices):
        UAH = 'UAH', 'Гривня',
        USD = 'USD', 'Долар',
        EUR = 'EUR', 'Євро',

    name = models.CharField(validators=[MaxLengthValidator(200)], max_length=200, verbose_name='Назва')
    type = models.CharField(max_length=20, default='Електро', verbose_name='Тип')
    licence_plate = models.CharField(validators=[MaxLengthValidator(24)], max_length=24,
                                     unique=True, verbose_name='Номерний знак')
    uber_uuid = models.CharField(null=True, max_length=36, verbose_name='Ідентифікатор авто в Uber')
    registration = models.CharField(null=True, max_length=12, unique=True, verbose_name='Номер документа')
    purchase_date = models.DateField(null=True, verbose_name='Дата початку роботи')
    start_mileage = models.IntegerField(default=0, verbose_name="Корекційний пробіг авто")
    vin_code = models.CharField(validators=[MaxLengthValidator(17)], max_length=17, blank=True)
    chat_id = models.CharField(max_length=15, blank=True, null=True, verbose_name="Група автомобіля телеграм")
    gps_imei = models.CharField(validators=[MaxLengthValidator(50)], max_length=50, blank=True, default='')
    coord_time = models.DateTimeField(null=True, verbose_name="Час отримання координат")
    lat = models.DecimalField(null=True, decimal_places=6, max_digits=10, default=0, verbose_name="Широта")
    lon = models.DecimalField(null=True, decimal_places=6, max_digits=10, default=0, verbose_name="Довгота")
    car_status = models.CharField(max_length=18, null=False, default="Serviceable", verbose_name='Статус автомобіля')
    purchase_price = models.DecimalField(decimal_places=2, max_digits=10, default=0, verbose_name="Вартість автомобіля")
    rental_price = models.IntegerField(default=0, verbose_name="Ціна оренди авто")
    currency = models.CharField(max_length=4, default=Currency.UAH, choices=Currency.choices,
                                verbose_name='Валюта покупки')
    currency_rate = models.DecimalField(decimal_places=2, max_digits=10, default=0,
                                        verbose_name="Курс валюти при покупці (НБУ)")
    car_earnings = models.DecimalField(decimal_places=2, max_digits=10, default=0, verbose_name="Заробіток авто")
    currency_back = models.CharField(max_length=4, default=Currency.USD, choices=Currency.choices,
                                     verbose_name='Валюта повернення коштів')
    investor_schema = models.CharField(max_length=15, choices=InvestorSchema.choices, blank=True, null=True,
                                       verbose_name='Схема інвестора')
    investor_percentage = models.DecimalField(decimal_places=2, max_digits=10, default=0.35,
                                              verbose_name="Відсоток інвестора")
    created_at = models.DateTimeField(editable=False, auto_now_add=True, verbose_name='Додано автомобіль')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Оновлено')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='Видалено')

    branding = models.ForeignKey(Fleet, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Бренд')
    manager = models.ForeignKey(Manager, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Менеджер авто')
    gps = models.ForeignKey(GPSNumber, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Назва авто в Gps")
    investor_car = models.ForeignKey(Investor, blank=True, null=True, on_delete=models.SET_NULL,
                                     verbose_name='Машина інвестора')
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Партнер')

    objects = SoftDeleteManager()

    class Meta:
        verbose_name = 'Автомобіль'
        verbose_name_plural = 'Автомобілі'

    def __str__(self) -> str:
        return f'{self.licence_plate}'

    @classmethod
    def filter_by_proportional_schema(cls, investors):
        return cls.objects.filter(investor_car__in=investors, investor_schema=InvestorSchema.Proportional)

    @classmethod
    def filter_by_share_schema(cls, investors):
        return cls.objects.filter(investor_car__in=investors, investor_schema=InvestorSchema.Equal_share)

    @classmethod
    def filter_by_rental_schema(cls, investors):
        return cls.objects.filter(investor_car__in=investors, investor_schema=InvestorSchema.Rental)


class DeletedVehicle(Vehicle):
    class Meta:
        verbose_name = 'Видалений автомобіль'
        verbose_name_plural = 'Видалені автомобілі'
        proxy = True


class VehicleSpending(models.Model):
    amount = models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Сума')
    description = models.TextField(blank=True, null=True, verbose_name='Опис')
    photo = models.ImageField(upload_to='spending/', blank=True, null=True, verbose_name='Фото')
    created_at = models.DateTimeField(editable=False, auto_now_add=True, verbose_name='Створено')

    spending_category = models.ForeignKey(SpendingCategory, null=True, on_delete=models.CASCADE,
                                          verbose_name='Категорія')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, null=True, verbose_name='Автомобіль')
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, null=True, verbose_name='Партнер')

    class Meta:
        verbose_name = 'Витрату'
        verbose_name_plural = 'Витрати'

    def __str__(self) -> str:
        return f'{self.vehicle} {self.spending_category}'


class Driver(User):
    ACTIVE = 'Онлайн'
    WITH_CLIENT = 'В дорозі'
    GET_ORDER = 'Приймаю замовлення'
    WAIT_FOR_CLIENT = 'Очікую клієнта'
    OFFLINE = 'Оффлайн'

    photo = models.ImageField(blank=True, null=True, upload_to='drivers', verbose_name='Фото водія',
                              default='drivers/default-driver.png')
    driver_status = models.CharField(max_length=35, default=OFFLINE, verbose_name='Статус водія')
    cash_control = models.BooleanField(default=True, verbose_name='Контроль готівки')
    cash_rate = models.DecimalField(decimal_places=2, max_digits=3, default=0, verbose_name='Дозволено готівки',
                                    validators=[
                                        MinValueValidator(0, message='Число повинно бути не менше 0.00'),
                                        MaxValueValidator(1, message='Число повинно бути не більше 1.00'),
                                    ])
    schema = models.ForeignKey(Schema, null=True, on_delete=models.SET_NULL, verbose_name='Схема роботи')
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, verbose_name='Партнер')
    manager = models.ForeignKey(Manager, on_delete=models.SET_NULL, null=True, blank=True,
                                verbose_name='Менеджер водіїв')

    class Meta:
        verbose_name = 'Водія'
        verbose_name_plural = 'Водії'

    def get_driver_external_id(self, fleet: Fleet):
        try:
            return FleetsDriversVehiclesRate.objects.get(fleet=fleet, driver=self,
                                                         partner=self.partner,
                                                         deleted_at__isnull=True).driver_external_id
        except ObjectDoesNotExist:
            return
        except MultipleObjectsReturned:
            print(self)
            return

    def get_bonuses(self):
        filter_query = Q(bonus__isnull=False, driver_payments__isnull=True)
        return self.penaltybonus_set.filter(filter_query).aggregate(Sum('amount'))['amount__sum'] or 0

    def get_penalties(self):
        filter_query = Q(penalty__isnull=False, driver_payments__isnull=True)
        return self.penaltybonus_set.filter(filter_query).aggregate(Sum('amount'))['amount__sum'] or 0



class FiredDriver(Driver):
    class Meta:
        verbose_name = 'Звільненого водія'
        verbose_name_plural = 'Звільнені водії'
        proxy = True


class PaymentsStatus(models.TextChoices):
    INCORRECT = 'incorrect', 'Потребує поправок'
    CHECKING = 'checking', 'Перевіряється'
    PENDING = 'pending', 'Очікується'
    COMPLETED = 'completed', 'Виплачений'
    FAILED = 'failed', 'Не сплачений'


class Earnings(PolymorphicModel):
    report_from = models.DateTimeField(verbose_name="Дохід з")
    report_to = models.DateTimeField(verbose_name="Дохід по")
    earning = models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Сума доходу')
    salary = models.DecimalField(decimal_places=2, null=True, blank=True, max_digits=10, verbose_name='Зарплата')
    status = models.CharField(max_length=20, choices=PaymentsStatus.choices, default=PaymentsStatus.CHECKING)

    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, verbose_name='Партнер')

    def is_completed(self):
        return True if self.status == PaymentsStatus.COMPLETED else False

    def is_pending(self):
        return True if self.status == PaymentsStatus.PENDING else False

    def is_failed(self):
        return True if self.status == PaymentsStatus.FAILED else False


class DriverPayments(Earnings):
    kasa = models.DecimalField(decimal_places=2, max_digits=10, default=0, verbose_name='Заробіток за період')
    cash = models.DecimalField(decimal_places=2, max_digits=10, default=0, verbose_name='Готівка')
    payment_type = models.CharField(max_length=20, default=SalaryCalculation.WEEK, choices=SalaryCalculation.choices,
                                    verbose_name='Тип платежу')
    rent_distance = models.DecimalField(decimal_places=2, max_digits=10, default=0, verbose_name='Орендована дистанція')
    rent_price = models.IntegerField(default=6, verbose_name='Ціна оренди')
    rent = models.DecimalField(decimal_places=2, max_digits=10, default=0, verbose_name='Оренда авто')
    rate = models.IntegerField(default=0, verbose_name='Відсоток водія')
    bolt_screen = models.ImageField(blank=True, null=True, upload_to='bolt', verbose_name="Фото звіту Bolt")

    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, verbose_name="Водій")

    class Meta:
        verbose_name = 'Виплати водію'
        verbose_name_plural = 'Виплати водіям'

    def change_status(self, new_status):
        self.status = new_status
        self.save(update_fields=['status'])

    def get_bonuses(self, vehicle=None):
        filter_query = Q(bonus__isnull=False)
        if vehicle:
            filter_query &= Q(vehicle=vehicle)
        return self.penaltybonus_set.filter(filter_query).aggregate(Sum('amount'))['amount__sum'] or 0

    def get_penalties(self, vehicle=None):
        filter_query = Q(penalty__isnull=False)
        if vehicle:
            filter_query &= Q(vehicle=vehicle)
        return self.penaltybonus_set.filter(filter_query).aggregate(Sum('amount'))['amount__sum'] or 0

    def is_weekly(self):
        return True if self.payment_type == SalaryCalculation.WEEK else False

    def save(self, *args, **kwargs):
        self.salary = Decimal(str(self.cash)) + Decimal(str(self.earning))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.driver}"




class ChargeTransactions(models.Model):
    charge_id = models.IntegerField(unique=True, verbose_name="ID транзакції")
    start_time = models.DateTimeField(verbose_name="Початок зарядки")
    end_time = models.DateTimeField(verbose_name="Кінець зарядки")
    charge_amount = models.DecimalField(decimal_places=2, max_digits=8, verbose_name="Кількість")
    price = models.DecimalField(decimal_places=2, max_digits=4, verbose_name="Ціна")

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, null=True, verbose_name="Авто")
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, null=True, verbose_name="Водій")

    def get_penalty_amount(self):
        price = Decimal(str(self.price))
        charge_amount = Decimal(str(self.charge_amount))
        return price * charge_amount


class PenaltyBonus(PolymorphicModel):
    photo = models.ImageField(upload_to='penalty_bonus/', blank=True, null=True, verbose_name='Фото')
    amount = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='Сума')
    description = models.CharField(max_length=255, null=True, verbose_name='Опис')

    category = models.ForeignKey(Category, null=True, on_delete=models.CASCADE, verbose_name='Категорія')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Автомобіль')
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Водій')
    driver_payments = models.ForeignKey(DriverPayments, null=True, blank=True, verbose_name='Виплата водію',
                                        on_delete=models.CASCADE)
    created_at = models.DateTimeField(editable=False, auto_now_add=True, verbose_name='Створено')

    class Meta:
        verbose_name = 'Штраф/Бонус'
        verbose_name_plural = 'Штрафи та Бонуси'

    @classmethod
    def get_amount(cls, default=None):
        try:
            penalty_bonus = cls.objects.first()
        except (ProgrammingError, ObjectDoesNotExist):
            return default
        return penalty_bonus.amount


class Penalty(PenaltyBonus):
    charge = models.ForeignKey(ChargeTransactions, on_delete=models.CASCADE, null=True)


class Bonus(PenaltyBonus):
    pass


class InvestorPayments(Earnings):
    currency = models.CharField(max_length=4, verbose_name='Валюта покупки')
    currency_rate = models.DecimalField(decimal_places=2, max_digits=10, default=0, verbose_name="Курс валюти")
    sum_after_transaction = models.DecimalField(decimal_places=2, max_digits=10, verbose_name="Сума у валюті")

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Автомобіль')
    investor = models.ForeignKey(Investor, on_delete=models.SET_NULL, null=True, verbose_name='Інвестор')

    class Meta:
        verbose_name = 'Виплату інвестору'
        verbose_name_plural = 'Виплати інвестору'


class PartnerEarnings(Earnings):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Автомобіль')
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Водій')

    class Meta:
        verbose_name = 'Дохід'
        verbose_name_plural = 'Доходи'


class DriverReshuffle(models.Model):
    EVENT_TYPES = [
        ('accident', 'ДТП'),
        ('maintenance', 'Тех.Обслуговування'),
    ]

    calendar_event_id = models.CharField(max_length=100)
    swap_time = models.DateTimeField(verbose_name="Час початку зміни")
    end_time = models.DateTimeField(verbose_name="Час завершення зміни")
    created_at = models.DateTimeField(editable=False, auto_now_add=True, verbose_name='Створено')
    dtp_or_maintenance = models.CharField(max_length=100, choices=EVENT_TYPES, null=True, verbose_name='Тип події')

    swap_vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, verbose_name="Автомобіль")
    driver_start = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, verbose_name="Водій")
    partner = models.ForeignKey(Partner, null=True, on_delete=models.CASCADE, verbose_name='Партнер')

    class Meta:
        verbose_name = 'Календар водіїв'
        verbose_name_plural = 'Календар водіїв'


class RentInformation(models.Model):
    report_from = models.DateTimeField(verbose_name='Звіт з')
    report_to = models.DateTimeField(null=True, verbose_name='Звіт по')
    rent_distance = models.DecimalField(null=True, blank=True, max_digits=6,
                                        decimal_places=2, verbose_name='Орендована дистанція')
    created_at = models.DateTimeField(editable=False, auto_now_add=True, verbose_name='Створено')

    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, verbose_name='Водій')
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, verbose_name='Партнер')

    class Meta:
        verbose_name = 'Інформацію по оренді'
        verbose_name_plural = 'Інформація по орендах'


class VehicleRent(models.Model):
    report_from = models.DateTimeField(verbose_name='Звіт з')
    report_to = models.DateTimeField(verbose_name='Звіт по')
    rent_distance = models.DecimalField(null=True, blank=True, max_digits=6,
                                        decimal_places=2, verbose_name='Орендована дистанція')

    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, verbose_name='Водій')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, verbose_name="Автомобіль")
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, verbose_name='Партнер')


# class NinjaFleet(Fleet):
#
#     @staticmethod
#     def start_report_interval(day):
#         return timezone.localize(datetime.combine(day, time.min))
#
#     @staticmethod
#     def end_report_interval(day):
#         return timezone.localize(datetime.combine(day, time.max))
#
#     def download_report(self, day=None):
#         report = Payments.objects.filter(report_from=self.start_report_interval(day),
#                                          report_to=self.end_report_interval(day),
#                                          fleet=self)
#         return list(report)


class Client(User):
    class Meta:
        verbose_name = 'Клієнта'
        verbose_name_plural = 'Клієнти'


class ServiceStationManager(User):
    car_id = models.ManyToManyField('Vehicle', blank=True)
    fleet_id = models.ManyToManyField(Fleet, blank=True)
    service_station = models.OneToOneField('ServiceStation', on_delete=models.RESTRICT, verbose_name='Сервісний центр')

    class Meta:
        verbose_name = 'Менеджера сервісного центра'
        verbose_name_plural = 'Менеджери сервісних центрів'

    def __str__(self):
        return self.full_name()


class SupportManager(User):
    client_id = models.ManyToManyField(Client, blank=True)
    driver_id = models.ManyToManyField(Driver, blank=True)

    class Meta:
        verbose_name = 'Менеджера служби підтримки'
        verbose_name_plural = 'Менеджери служби підтримки'


class DriverReport(PolymorphicModel):
    report_from = models.DateTimeField(verbose_name='Звіт з')
    report_to = models.DateTimeField(null=True, verbose_name='Звіт по')
    total_amount_without_fee = models.DecimalField(decimal_places=2, max_digits=10,
                                                   verbose_name='Чистий дохід')
    total_amount_cash = models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Готівкою')
    total_amount_on_card = models.DecimalField(null=True, decimal_places=2, max_digits=10, verbose_name='На картку')
    total_amount = models.DecimalField(null=True, decimal_places=2, max_digits=10, verbose_name='Загальна сума')
    total_rides = models.PositiveIntegerField(null=True, verbose_name='Кількість поїздок')
    total_distance = models.DecimalField(null=True, decimal_places=2,
                                         max_digits=10, verbose_name='Пробіг під замовленням')
    tips = models.DecimalField(null=True, decimal_places=2, max_digits=10, verbose_name='Чайові')
    bonuses = models.DecimalField(null=True, decimal_places=2, max_digits=10, verbose_name='Бонуси')
    fee = models.DecimalField(null=True, decimal_places=2, max_digits=10, verbose_name='Комісія')
    fares = models.DecimalField(null=True, decimal_places=2, max_digits=10, verbose_name='Штрафи')
    cancels = models.DecimalField(null=True, decimal_places=2, max_digits=10, verbose_name='Плата за скасування')
    compensations = models.DecimalField(null=True, decimal_places=2, max_digits=10, verbose_name='Компенсації')
    refunds = models.DecimalField(null=True, decimal_places=2, max_digits=10, verbose_name='Повернення коштів')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Створено')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Оновлено')

    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Партнер')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Автомобіль')
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, null=True, verbose_name='Водій')


class Payments(DriverReport):
    fleet = models.ForeignKey(Fleet, on_delete=models.CASCADE, verbose_name='Агрегатор')

    class Meta:
        verbose_name = 'Звіт'
        verbose_name_plural = 'Звіти'


class SummaryReport(DriverReport):
    class Meta:
        verbose_name = 'Зведений звіт'
        verbose_name_plural = 'Зведені звіти'


class CustomReport(DriverReport):
    fleet = models.ForeignKey(Fleet, on_delete=models.CASCADE, verbose_name='Агрегатор')


class WeeklyReport(DriverReport):
    fleet = models.ForeignKey(Fleet, on_delete=models.CASCADE, verbose_name='Агрегатор')

    class Meta:
        verbose_name = 'Тижневий звіт'
        verbose_name_plural = 'Тижневі звіти'


class DailyReport(DriverReport):
    fleet = models.ForeignKey(Fleet, on_delete=models.CASCADE, verbose_name='Агрегатор')

    class Meta:
        verbose_name = 'Денний звіт'
        verbose_name_plural = 'Денні звіти'


class StatusChange(models.Model):
    name = models.CharField(max_length=255, verbose_name='Назва статусу')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)

    driver = models.ForeignKey(Driver, null=True, on_delete=models.CASCADE)
    vehicle = models.ForeignKey(Vehicle, null=True, on_delete=models.CASCADE)


class FleetsDriversVehiclesRate(models.Model):
    pay_cash = models.BooleanField(default=True, verbose_name='Оплата готівкою')
    driver_external_id = models.CharField(max_length=255, verbose_name='Унікальний ідентифікатор по автопарку')

    created_at = models.DateTimeField(editable=False, auto_now_add=True, verbose_name='Створено')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Оновлено')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='Видалено')

    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, verbose_name='Партнер')
    fleet = models.ForeignKey(Fleet, on_delete=models.CASCADE, verbose_name='Агрегатор')
    driver = models.ForeignKey(Driver, null=True, on_delete=models.CASCADE, verbose_name='Водій')

    def __str__(self) -> str:
        return ''

    class Meta:
        verbose_name = 'Водія в агрегаторах'
        verbose_name_plural = 'Водії в агрегаторах'


class DriverSchemaRate(models.Model):
    period = models.CharField(max_length=25, choices=SalaryCalculation.choices, verbose_name='Період розрахунку')
    threshold = models.DecimalField(decimal_places=2, max_digits=15, default=0, verbose_name="Поріг доходу")
    rate = models.DecimalField(decimal_places=2, max_digits=3, default=0, verbose_name="Відсоток")

    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, verbose_name='Партнер')

    class Meta:
        verbose_name = 'Тариф водія'
        verbose_name_plural = 'Тарифи водія'

    @staticmethod
    def get_rate_tier(period, partner):
        data = DriverSchemaRate.objects.filter(period=period,
                                               partner=partner).order_by('threshold').values('threshold', 'rate')
        result = [(decimal['threshold'], decimal['rate']) for decimal in data]
        return result


class RawGPS(models.Model):
    imei = models.CharField(max_length=100)
    client_ip = models.CharField(max_length=100)
    client_port = models.IntegerField()
    data = models.CharField(max_length=1024)
    created_at = models.DateTimeField(editable=False, auto_now_add=True)

    class Meta:
        verbose_name = 'GPS Raw'
        verbose_name_plural = 'GPS Raw'
        indexes = [
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f'{self.data}'


class GPS(PolymorphicModel):
    date_time = models.DateTimeField(null=False)
    lat = models.DecimalField(decimal_places=6, max_digits=10, default=0)
    lat_zone = models.CharField(max_length=1)
    lon = models.DecimalField(decimal_places=6, max_digits=10, default=0)
    lon_zone = models.CharField(max_length=1)
    speed = models.IntegerField(default=0)
    course = models.IntegerField(default=0)
    height = models.IntegerField(default=0)
    created_at = models.DateTimeField(editable=False, auto_now_add=True)

    def __str__(self):
        return f'{self.lat}{self.lat_zone}:{self.lon}{self.lon_zone}'


class VehicleGPS(GPS):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    raw_data = models.OneToOneField(RawGPS, null=True, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'GPS Vehicle'
        verbose_name_plural = 'GPS Vehicle'
        indexes = [
            models.Index(fields=['raw_data']),
            models.Index(fields=['raw_data'], name='raw_data_null', condition=models.Q(raw_data__isnull=True)),
        ]


class RepairReport(models.Model):
    repair = models.CharField(max_length=255, verbose_name='Фото звіту про ремонт')
    numberplate = models.CharField(max_length=12, unique=True, verbose_name='Номер автомобіля')
    start_of_repair = models.DateTimeField(blank=True, null=False, verbose_name='Початок ремонту')
    end_of_repair = models.DateTimeField(blank=True, null=False, verbose_name='Закінчення ремонту')
    status_of_payment_repair = models.BooleanField(default=False, verbose_name='Статус оплати')  # Paid, Unpaid

    driver = models.ForeignKey(Driver, null=True, blank=True, on_delete=models.CASCADE, verbose_name='Водій')

    class Meta:
        verbose_name = 'Звіт про ремонт'
        verbose_name_plural = 'Звіти про ремонти'

    def __str__(self):
        return f'{self.numberplate}'


class ServiceStation(models.Model):
    name = models.CharField(max_length=120, verbose_name='Назва')
    owner = models.CharField(max_length=150, verbose_name='Власник')
    lat = models.DecimalField(decimal_places=4, max_digits=10, default=0, verbose_name='Широта')
    lat_zone = models.CharField(max_length=1, verbose_name='Пояс-Широти')
    lon = models.DecimalField(decimal_places=4, max_digits=10, default=0, verbose_name='Довгота')
    lon_zone = models.CharField(max_length=1, verbose_name='Пояс-Довготи')
    description = models.CharField(max_length=255, verbose_name='Опис')

    class Meta:
        verbose_name = "Сервісний Центр"
        verbose_name_plural = 'Сервісні центри'

    def __str__(self):
        return f'{self.name}'


class Comment(models.Model):
    comment = models.TextField(verbose_name='Відгук')
    chat_id = models.CharField(blank=True, max_length=10, verbose_name='ID в чаті')
    processed = models.BooleanField(default=False, verbose_name='Опрацьовано')

    created_at = models.DateTimeField(editable=False, auto_now_add=True, verbose_name='Створено')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Оновлено')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='Видалено')

    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Партнер')

    def __str__(self):
        return self.comment

    class Meta:
        verbose_name = 'Відгук'
        verbose_name_plural = 'Відгуки'
        ordering = ['-created_at']


class Order(models.Model):
    WAITING = 'Очікується'
    IN_PROGRESS = 'Виконується'
    COMPLETED = 'Виконаний'
    CANCELED = 'Скасовано клієнтом'
    ON_TIME = 'На певний час'

    STANDARD_TYPE = 'Звичайне замовлення'
    PERSONAL_TYPE = 'Персональний водій'

    from_address = models.CharField(max_length=255, verbose_name='Місце посадки')
    latitude = models.CharField(max_length=10, verbose_name='Широта місця посадки')
    longitude = models.CharField(max_length=10, verbose_name='Довгота місця посадки')
    to_the_address = models.CharField(max_length=255, blank=True, null=True, verbose_name='Місце висадки')
    to_latitude = models.CharField(max_length=10, null=True, verbose_name='Широта місця висадки')
    to_longitude = models.CharField(max_length=10, null=True, verbose_name='Довгота місця висадки')
    phone_number = models.CharField(max_length=13, verbose_name='Номер телефона клієнта')
    chat_id_client = models.CharField(max_length=10, blank=True, null=True, verbose_name='Ідентифікатор чату клієнта')
    type_order = models.CharField(max_length=100, default=STANDARD_TYPE, verbose_name='Тип замовлення')
    info = models.CharField(max_length=255, null=True, verbose_name='Додаткова інформація')
    car_delivery_price = models.IntegerField(default=0, verbose_name='Сума за подачу автомобіля')
    sum = models.IntegerField(default=0, verbose_name='Загальна сума')
    order_time = models.DateTimeField(null=True, blank=True, verbose_name='Час подачі')
    payment_hours = models.IntegerField(null=True, verbose_name='Годин Сплачено')
    payment_method = models.CharField(max_length=70, default="Картка", verbose_name='Спосіб оплати')
    status_order = models.CharField(max_length=70, verbose_name='Статус замовлення')
    distance_gps = models.CharField(max_length=10, blank=True, null=True, verbose_name='Дистанція по GPS')
    distance_google = models.CharField(max_length=10, verbose_name='Дистанція Google')
    accepted_time = models.DateTimeField(blank=True, null=True, verbose_name='Час прийняття замовлення')
    finish_time = models.DateTimeField(blank=True, null=True, verbose_name='Час завершення замовлення')
    created_at = models.DateTimeField(editable=False, auto_now_add=True, verbose_name='Cтворено')
    comment = models.OneToOneField(Comment, null=True, on_delete=models.SET_NULL, verbose_name='Відгук')
    checked = models.BooleanField(default=False, verbose_name='Перевірено')

    driver = models.ForeignKey(Driver, null=True, on_delete=models.RESTRICT, verbose_name='Виконувач')
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Партнер')

    class Meta:
        verbose_name = 'Замовлення'
        verbose_name_plural = 'Замовлення'

    def __str__(self):
        return f'Замовлення №{self.pk}'


class ReportTelegramPayments(models.Model):
    provider_payment_charge_id = models.CharField(max_length=50,
                                                  verbose_name='Ідентифікатор оплати в провайдері')
    telegram_payment_charge_id = models.CharField(max_length=50,
                                                  verbose_name='Ідентифікатор оплати в телеграмі')
    currency = models.CharField(max_length=24, verbose_name='Валюта')
    total_amount = models.PositiveIntegerField(verbose_name='Сума оплати')

    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Замовлення')

    class Meta:
        verbose_name = 'Звіт про оплату в телеграмі'
        verbose_name_plural = 'Звіти про оплату в телеграмі'

    def __str__(self):
        return self.provider_payment_charge_id


class FleetOrder(models.Model):
    SYSTEM_CANCEL = 'Скасовано системою'
    COMPLETED = 'Виконаний'
    CLIENT_CANCEL = 'Скасовано клієнтом'
    DRIVER_CANCEL = 'Скасовано водієм'

    order_id = models.CharField(max_length=50, verbose_name='Ідентифікатор замовлення')
    fleet = models.CharField(max_length=20, verbose_name='Агрегатор замовлення')
    from_address = models.CharField(max_length=255, null=True, verbose_name='Місце посадки')
    destination = models.CharField(max_length=255, blank=True, null=True, verbose_name='Місце висадки')
    accepted_time = models.DateTimeField(blank=True, null=True, verbose_name='Час прийняття замовлення')
    finish_time = models.DateTimeField(blank=True, null=True, verbose_name='Час завершення замовлення')
    distance = models.DecimalField(null=True, decimal_places=2, max_digits=6, verbose_name="Відстань за маршрутом")
    fleet_distance = models.DecimalField(null=True, decimal_places=2, max_digits=6,
                                         verbose_name="Відстань в агрегаторі")
    road_time = models.DurationField(null=True, blank=True, verbose_name='Час в дорозі')
    state = models.CharField(max_length=255, blank=True, null=True, verbose_name='Статус замовлення')
    payment = models.CharField(max_length=25, choices=PaymentTypes.choices, null=True, verbose_name="Тип оплати")
    price = models.IntegerField(null=True, verbose_name="Вартість")
    tips = models.IntegerField(null=True, verbose_name="Чайові")
    date_order = models.DateTimeField(null=True, verbose_name='Дата замовлення')
    created_at = models.DateTimeField(editable=False, auto_now_add=True, verbose_name='Cтворено')

    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Водій')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Автомобіль')
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Партнер')

    class Meta:
        verbose_name = 'Замовлення в агрегаторах'
        verbose_name_plural = 'Замовлення в агрегаторах'


class ReportDriveDebt(models.Model):
    driver = models.CharField(max_length=255, verbose_name='Водій')
    image = models.ImageField(upload_to='.', verbose_name='Фото')
    created_at = models.DateTimeField(editable=False, auto_now_add=True, verbose_name='Створено')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Оновлено')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='Видалено')

    class Meta:
        verbose_name = 'Звіт заборгованості водія'
        verbose_name_plural = 'Звіти заборгованості водіїв'
        ordering = ['driver']


class Event(models.Model):
    SICK_DAY = "Лікарняний"
    DAY_OFF = "Вихідний"
    full_name_driver = models.CharField(max_length=255, verbose_name='Водій')
    event = models.CharField(max_length=20, verbose_name='Подія')
    event_date = models.DateTimeField(null=True, blank=True, verbose_name='Час події')
    chat_id = models.CharField(blank=True, max_length=10, verbose_name='Ідентифікатор чата')
    created_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Створено')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Оновлено')

    class Meta:
        verbose_name = 'Відпочинок і лікування'
        verbose_name_plural = 'Відпочинки і лікування'


class SubscribeUsers(models.Model):
    email = models.EmailField(max_length=254, verbose_name='Електронна пошта')
    name = models.CharField(max_length=100, verbose_name='Ім\'я')
    phone_number = models.CharField(max_length=15, verbose_name='Номер телефону')
    created_at = models.DateTimeField(editable=False, auto_now=True, verbose_name='Створено')

    class Meta:
        verbose_name = 'Підписника'
        verbose_name_plural = 'Підписники'

    @staticmethod
    def get_by_email(email):
        """
        Returns subscriber by field
        :param email: email by which we need to find the subscriber
        :type email: str
        :return: subscriber object or None if a subscriber with such email does not exist
        """
        try:
            subscriber = SubscribeUsers.objects.get(email=email)
            return subscriber
        except ObjectDoesNotExist:
            return None


class JobApplication(models.Model):
    first_name = models.CharField(max_length=255, verbose_name='Ім\'я')
    last_name = models.CharField(max_length=255, verbose_name='Прізвище')
    email = models.EmailField(max_length=255, verbose_name='Електронна пошта')
    chat_id = models.CharField(blank=True, max_length=10, verbose_name='Ідентифікатор чата')
    password = models.CharField(max_length=12, verbose_name='Пароль Uklon')
    phone_number = models.CharField(max_length=20, verbose_name='Телефон')
    license_expired = models.DateField(blank=True, verbose_name='Термін дії посвідчення')
    driver_license_front = models.ImageField(blank=True, upload_to='job/licenses/front',
                                             verbose_name='Лицьова сторона посвідчення')
    driver_license_back = models.ImageField(blank=True, upload_to='job/licenses/back',
                                            verbose_name='Тильна сторона посвідчення')
    photo = models.ImageField(blank=True, upload_to='job/photo', verbose_name='Фото водія')
    car_documents = models.ImageField(blank=True, upload_to='job/car', default="docs/default_car.jpg",
                                      verbose_name='Фото техпаспорту', )
    insurance = models.ImageField(blank=True, upload_to='job/insurance', default="docs/default_insurance.png",
                                  verbose_name='Автоцивілка')
    insurance_expired = models.DateField(default=date(2023, 12, 15), verbose_name='Термін дії автоцивілки')
    role = models.CharField(max_length=255, verbose_name='Роль')
    status_bolt = models.DateField(null=True, verbose_name='Опрацьована BOLT')
    status_uklon = models.DateField(null=True, verbose_name='Опрацьована Uklon')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата подачі заявки')

    def save(self, *args, **kwargs):
        if not self.pk:
            self.password = self.generate_password()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_password(length=12):
        chars = string.ascii_lowercase + string.digits
        password = ''.join(random.choice(chars) for _ in range(length - 2))
        password += random.choice(string.ascii_uppercase)
        password += random.choice(string.digits)
        return ''.join(random.sample(password, len(password)))

    def admin_photo(self):
        return admin_image_preview(self.photo)

    def admin_front(self):
        return admin_image_preview(self.driver_license_front)

    def admin_back(self):
        return admin_image_preview(self.driver_license_back)

    def admin_insurance(self):
        return admin_image_preview(self.insurance)

    def admin_car_document(self):
        return admin_image_preview(self.car_documents)

    admin_back.short_description = 'License back'
    admin_photo.short_description = 'Photo'
    admin_front.short_description = 'License front'
    admin_insurance.short_description = 'Insurance'
    admin_car_document.short_description = 'Car document'

    class Meta:
        verbose_name = 'Заявку'
        verbose_name_plural = 'Заявки'

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


def admin_image_preview(image):
    if image:
        url = image.url
        return mark_safe(f'<a href="{url}"><img src="{url}" width="200" height="150"></a>')
    return None


class CarEfficiency(models.Model):
    report_from = models.DateTimeField(verbose_name='Звіт з')
    report_to = models.DateTimeField(null=True, verbose_name='Звіт по')
    total_kasa = models.DecimalField(decimal_places=2, max_digits=10, default=0, verbose_name='Каса')
    clean_kasa = models.DecimalField(decimal_places=2, max_digits=10, default=0, verbose_name='Чистий дохід')
    total_spending = models.DecimalField(null=True, decimal_places=2, max_digits=10, default=0, verbose_name='Витрати')
    mileage = models.DecimalField(decimal_places=2, max_digits=10, default=0, verbose_name='Пробіг, км')
    efficiency = models.DecimalField(decimal_places=2, max_digits=4, default=0, verbose_name='Ефективність, грн/км')
    total_brand_trips = models.IntegerField(default=0, verbose_name='Всього поїздок бренду')

    drivers = models.ManyToManyField(Driver, through="DriverEffVehicleKasa", verbose_name='Водії', db_index=True)
    vehicle = models.ForeignKey(Vehicle, null=True, on_delete=models.CASCADE, verbose_name='Автомобіль', db_index=True)
    partner = models.ForeignKey(Partner, null=True, on_delete=models.SET_NULL, verbose_name='Партнер')
    investor = models.ForeignKey(Investor, null=True, on_delete=models.SET_NULL, verbose_name='Інвестор')

    class Meta:
        verbose_name = 'Ефективність автомобіля'
        verbose_name_plural = 'Ефективність автомобілів'

    def __str__(self):
        return str(self.vehicle)


class DriverEffVehicleKasa(models.Model):
    kasa = models.DecimalField(max_digits=10, decimal_places=2)

    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)
    efficiency_car = models.ForeignKey(CarEfficiency, on_delete=models.CASCADE)


class DriverEfficiencyPolymorphic(PolymorphicModel):
    report_from = models.DateTimeField(verbose_name='Звіт з')
    report_to = models.DateTimeField(null=True, verbose_name='Звіт по')
    total_kasa = models.DecimalField(decimal_places=2, max_digits=10, default=0, verbose_name='Каса')
    total_orders = models.IntegerField(default=0, verbose_name="Замовлень за день")
    total_orders_rejected = models.IntegerField(default=0, verbose_name="Відмов в замовленнях")
    total_orders_accepted = models.IntegerField(default=0, verbose_name="Прийнято замовлень")
    accept_percent = models.IntegerField(default=0, verbose_name="Відсоток прийнятих замовлень")
    average_price = models.DecimalField(decimal_places=2, max_digits=6, default=0, verbose_name='Середній чек, грн')
    mileage = models.DecimalField(decimal_places=2, max_digits=10, default=0, verbose_name='Пробіг, км')
    efficiency = models.DecimalField(decimal_places=2, max_digits=6, default=0, verbose_name='Ефективність, грн/км')
    road_time = models.DurationField(null=True, blank=True, verbose_name='Час в дорозі')

    partner = models.ForeignKey(Partner, null=True, on_delete=models.CASCADE, verbose_name='Партнер')
    driver = models.ForeignKey(Driver, null=True, on_delete=models.SET_NULL, verbose_name='Водій', db_index=True)
    vehicles = models.ManyToManyField(Vehicle, verbose_name="Автомобілі", db_index=True)

    def __str__(self):
        return f"{self.driver}"


class DriverEfficiency(DriverEfficiencyPolymorphic):
    rent_distance = models.DecimalField(decimal_places=2, max_digits=10, default=0, verbose_name='Холостий пробіг')
    total_cash = models.DecimalField(decimal_places=2, max_digits=10, default=0, verbose_name='Готівкою')

    class Meta:
        verbose_name = 'Ефективність водія'
        verbose_name_plural = 'Ефективність водіїв'


class DriverEfficiencyFleet(DriverEfficiencyPolymorphic):
    fleet = models.ForeignKey(Fleet, null=True, on_delete=models.CASCADE, verbose_name='Агрегатор')

    class Meta:
        verbose_name = 'Ефективність водія в агрегаторах'
        verbose_name_plural = 'Ефективність водіїв в агрегаторах'


class UseOfCars(models.Model):
    user_vehicle = models.CharField(max_length=255, verbose_name='Користувач автомобіля')
    chat_id = models.CharField(blank=True, max_length=10, verbose_name='Ідентифікатор чата')
    licence_plate = models.CharField(max_length=24, verbose_name='Номерний знак')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата використання авто')
    end_at = models.DateTimeField(null=True, blank=True, verbose_name='Кінець використання авто')

    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Партнер')

    class Meta:
        verbose_name = 'Користувача автомобіля'
        verbose_name_plural = 'Користувачі автомобілів'

    def __str__(self):
        return f"{self.user_vehicle}: {self.licence_plate}"


class ParkSettings(models.Model):
    key = models.CharField(max_length=255, verbose_name='Ключ')
    value = models.CharField(max_length=255, verbose_name='Значення')
    description = models.CharField(max_length=255, null=True, verbose_name='Опиc')

    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Партнер')

    class Meta:
        verbose_name = 'Налаштування автопарка'
        verbose_name_plural = 'Налаштування автопарків'

    def __str__(self):
        return f'{self.value}'

    @staticmethod
    def get_value(key, default=None, **kwargs):
        try:
            setting = ParkSettings.objects.get(key=key, **kwargs)
        except ObjectDoesNotExist:
            return default
        return setting.value


class CredentialPartner(models.Model):
    key = models.CharField(max_length=255, verbose_name='Ключ')
    value = models.BinaryField(verbose_name='Значення')

    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Партнер')

    @staticmethod
    def encrypt_credential(value):
        return Fernet(os.environ.get("CRYPT_KEY").encode('utf-8')).encrypt(value.encode())

    @staticmethod
    def decrypt_credential(value):
        key = os.environ.get("CRYPT_KEY").encode('utf-8')
        return Fernet(key).decrypt(value).decode()

    @staticmethod
    def get_value(key, default=None, **kwargs):
        try:
            setting = CredentialPartner.objects.get(key=key, **kwargs)
        except ObjectDoesNotExist:
            return default
        return setting.decrypt_credential(bytes(setting.value))


class Service(PolymorphicModel):
    key = models.CharField(max_length=255, verbose_name='Ключ')
    value = models.CharField(max_length=255, verbose_name='Значення')
    description = models.CharField(max_length=255, null=True, verbose_name='Опиc')

    class Meta:
        verbose_name = 'Сервіс'
        verbose_name_plural = 'Сервіси'

    @classmethod
    def get_value(cls, key, default=None):
        try:
            setting = cls.objects.get(key=key)
        except (ProgrammingError, ObjectDoesNotExist):
            return default
        return setting.value


class BoltService(Service):
    pass


class NewUklonService(Service):
    pass


class UaGpsService(Service):
    pass


class UberService(Service):
    pass


class UberSession(models.Model):
    session = models.CharField(max_length=255, verbose_name='Ідентифікатор сесії')
    cook_session = models.CharField(max_length=255, verbose_name='Ідентифікатор cookie')
    uber_uuid = models.UUIDField(verbose_name="Код автопарку Uber")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Створено')

    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Партнер')


class UserBank(models.Model):
    chat_id = models.CharField(blank=True, max_length=10, verbose_name='Ідентифікатор чата')
    duty = models.IntegerField(default=0, verbose_name='Борг')

    class Meta:
        verbose_name = 'Банк боргів'
        verbose_name_plural = 'Банк боргів'

    @staticmethod
    def get_duty(chat_id):
        return UserBank.objects.filter(chat_id=chat_id).first()
