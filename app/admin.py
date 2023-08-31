from django.contrib import admin
from django.contrib.admin import AdminSite
from django.forms import BaseInlineFormSet
from django.utils import timezone

from taxi_service.views import *
from .models import *
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save
from django.dispatch import receiver


models = {
    'RentInformation':              {'view': True, 'add': False, 'change': False, 'delete': False},
    'Payments':                     {'view': True, 'add': False, 'change': False, 'delete': False},
    'SummaryReport':                {'view': True, 'add': False, 'change': False, 'delete': False},
    'Order':                        {'view': True, 'add': False, 'change': False, 'delete': False},
    'Driver':                       {'view': True, 'add': True, 'change': True, 'delete': True},
    'Vehicle':                      {'view': True, 'add': True, 'change': True, 'delete': True},
    'Manager':                      {'view': True, 'add': True, 'change': True, 'delete': True},
    'Comment':                      {'view': True, 'add': False, 'change': True, 'delete': False},
    'ParkSettings':                 {'view': True, 'add': False, 'change': True, 'delete': False},
    'CarEfficiency':                {'view': True, 'add': False, 'change': False, 'delete': False},
    'DriverEfficiency':             {'view': True, 'add': False, 'change': False, 'delete': False}
}

investor_permissions = {
    'Vehicle':                      {'view': True, 'add': False, 'change': False, 'delete': False},
    'CarEfficiency':                {'view': True, 'add': False, 'change': False, 'delete': False},
    'VehicleSpendings':             {'view': True, 'add': False, 'change': False, 'delete': False},
    'Dashboard':                    {'view': True, 'add': False, 'change': False, 'delete': False},
}


def assign_model_permissions(group, permissions):
    for model, permissions in permissions.items():
        content_type = ContentType.objects.get(app_label='app', model__iexact=model)
        model_permissions = Permission.objects.filter(content_type=content_type)

        for permission, value in permissions.items():
            codename = f'{permission}_{model.lower()}'
            permission_obj = model_permissions.get(codename=codename)

            if value and permission_obj not in group.permissions.all():
                group.permissions.add(permission_obj)

try:
    group1, created = Group.objects.get_or_create(name='Partner')
    for user in group1.user_set.all():
        for permission in group1.permissions.all():
            user.user_permissions.add(permission)
    assign_model_permissions(group1, models)

    group2, created = Group.objects.get_or_create(name='Investor')
    assign_model_permissions(group2, investor_permissions)

    group3, created = Group.objects.get_or_create(name='Manager')
    for user in group3.user_set.all():
        for permission in group3.permissions.all():
            user.user_permissions.add(permission)
    assign_model_permissions(group3, models)
except (ProgrammingError, ObjectDoesNotExist):
    pass


@receiver(post_save, sender=Group)
def add_partner_permissions(sender, instance, created, **kwargs):
    if created and instance.name == 'partner':
        assign_model_permissions(instance)
        for user in instance.user_set.all():
            assign_model_permissions(user)


def filter_queryset_by_group(*groups):
    def decorator(model_admin_class):
        class FilteredModelAdmin(model_admin_class):
            def get_queryset(self, request):
                queryset = super().get_queryset(request)

                if request.user.groups.filter(name='Investor').exists():

                    investor_vehicles = Vehicle.objects.filter(investor_car__user=request.user)
                    investor_vehicle_ids = investor_vehicles.values_list('licence_plate', flat=True)

                    queryset = queryset.filter(licence_plate__in=investor_vehicle_ids)

                if request.user.groups.filter(name='Manager').exists():
                    queryset = queryset.filter(manager__user=request.user)
                if request.user.groups.filter(name='Partner').exists():
                    queryset = queryset.filter(partner__user=request.user)

                return queryset

        return FilteredModelAdmin

    return decorator


def add_partner_on_save_model(*models):
    def decorator(admin_class):
        original_save_model = admin_class.save_model

        def save_model(self, request, obj, form, change):
            if not change and not obj.partner_id:
                if request.user.is_superuser:
                    pass
                else:
                    partner = Partner.objects.get(user=request.user)
                    if partner:
                        obj.partner_id = partner.pk
            elif change and 'partner_id' not in form.changed_data:
                obj.partner_id = obj.partner_id
            original_save_model(self, request, obj, form, change)

        admin_class.save_model = save_model
        return admin_class

    return decorator


# class FleetChildAdmin(PolymorphicChildModelAdmin):
#     base_model = Fleet
#     show_in_index = False
#
#
# @admin.register(UberFleet)
# class UberFleetAdmin(FleetChildAdmin):
#     base_model = UberFleet
#     show_in_index = False
#
#
# @admin.register(BoltFleet)
# class BoltFleetAdmin(FleetChildAdmin):
#     base_model = BoltFleet
#     show_in_index = False
#
#
# @admin.register(UklonFleet)
# class UklonFleetAdmin(FleetChildAdmin):
#     base_model = UklonFleet
#     show_in_index = False
#
# @admin.register(NewUklonFleet)
# class UklonFleetAdmin(FleetChildAdmin):
#     base_model = NewUklonFleet
#     show_in_index = False
#
#
# @admin.register(Fleet)
# class FleetParentAdmin(PolymorphicParentModelAdmin):
#     base_model = Fleet
#     child_models = (UberFleet, BoltFleet, UklonFleet, NewUklonFleet, NinjaFleet)
#     list_filter = PolymorphicChildModelFilter
#
#
#  @admin.register(NinjaFleet)
# class NinjaFleetAdmin(FleetChildAdmin):
#     base_model = NinjaFleet
#     show_in_index = False


class SupportManagerClientInline(admin.TabularInline):
    model = SupportManager.client_id.through
    extra = 0

    def __init__(self, parent_model, admin_site):
        super().__init__(parent_model, admin_site)
        if parent_model is Client:
            self.verbose_name = 'Менеджер служби підтримки'
            self.verbose_name_plural = 'Менеджери служби підтримки'
        if parent_model is SupportManager:
            self.verbose_name = 'Клієнт'
            self.verbose_name_plural = 'Клієнти'


class SupportManagerDriverInline(admin.TabularInline):
    model = SupportManager.driver_id.through
    extra = 0

    def __init__(self, parent_model, admin_site):
        super().__init__(parent_model, admin_site)
        if parent_model is Driver:
            self.verbose_name = 'Менеджер служби підтримки'
            self.verbose_name_plural = 'Менеджери служби підтримки'
        if parent_model is SupportManager:
            self.verbose_name = 'Водій'
            self.verbose_name_plural = 'Водії'


class ServiceStationManagerVehicleInline(admin.TabularInline):
    model = ServiceStationManager.car_id.through
    extra = 0

    def __init__(self, parent_model, admin_site):
        super().__init__(parent_model, admin_site)
        if parent_model is Vehicle:
            self.verbose_name = 'Менеджер сервісного центру'
            self.verbose_name_plural = 'Менеджери сервісного центру'
        if parent_model is ServiceStationManager:
            self.verbose_name = 'Автомобіль'
            self.verbose_name_plural = 'Автомобілі'


class ServiceStationManagerFleetInline(admin.TabularInline):
    model = ServiceStationManager.fleet_id.through
    extra = 0

    def __init__(self, parent_model, admin_site):
        super().__init__(parent_model, admin_site)
        if parent_model is Fleet:
            self.verbose_name = 'Менеджер сервісного центру'
            self.verbose_name_plural = 'Менеджери сервісного центру'
        if parent_model is ServiceStationManager:
            self.verbose_name = 'Автопарк'
            self.verbose_name_plural = 'Автопарки'


class Fleets_drivers_vehicles_rateInline(admin.TabularInline):
    model = Fleets_drivers_vehicles_rate
    extra = 0
    verbose_name = 'Fleets Drivers Vehicles Rate'
    verbose_name_plural = 'Fleets Drivers Vehicles Rate'

    fieldsets = [
        (None, {'fields': ['fleet', 'driver', 'vehicle', 'driver_external_id', 'rate']}),
    ]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name in ('vehicle', 'driver'):
            partner = self.get_parent_instance(request)

            if partner:
                kwargs['queryset'] = db_field.related_model.objects.filter(partner=partner)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_parent_instance(self, request):
        return Partner.objects.get(user=request.user.pk)


@admin.register(Fleet)
class FleetAdmin(admin.ModelAdmin):
    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DriverRateLevels)
class DriverRateLevelsAdmin(admin.ModelAdmin):
    list_display = [f.name for f in DriverRateLevels._meta.fields]
    list_per_page = 25

    fieldsets = [
        (None, {'fields': ['fleet', 'threshold_value', 'rate_delta']}),
    ]


@admin.register(RawGPS)
class RawGPSAdmin(admin.ModelAdmin):
    list_display = ('imei', 'client_ip', 'client_port', 'data_', 'created_at', 'vehiclegps')
    list_display_links = ('imei', 'client_ip', 'client_port', 'data_')
    search_fields = ('imei',)
    list_filter = ('imei', 'client_ip', 'created_at')
    ordering = ('-created_at', 'imei')
    list_per_page = 25

    def data_(self, instance):
        return f'{instance.data[:100]}...'


@admin.register(VehicleGPS)
class VehicleGPSAdmin(admin.ModelAdmin):
    list_display = (
        'vehicle', 'date_time', 'lat', 'lat_zone', 'lon', 'lon_zone', 'speed', 'course', 'height', 'created_at')
    search_fields = ('vehicle',)
    list_filter = ('vehicle', 'date_time', 'created_at')
    ordering = ('-date_time', 'vehicle')
    list_per_page = 25


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('name', 'second_name', 'email', 'phone_number', 'role', 'created_at')
    list_display_links = ('name', 'second_name')
    list_filter = ['created_at', 'role']
    search_fields = ('name', 'second_name')
    ordering = ('name', 'second_name')
    list_per_page = 25

    fieldsets = [
        (None, {'fields': ['name', 'second_name', 'email', 'role', 'phone_number']}),
    ]


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'second_name', 'email', 'phone_number', 'created_at')
    list_display_links = ('name', 'second_name')
    list_filter = ['created_at']
    search_fields = ('name', 'second_name')
    ordering = ('name', 'second_name')
    list_per_page = 25

    fieldsets = [
        (None, {'fields': ['name', 'second_name', 'email', 'phone_number']}),
    ]

    inlines = [
        SupportManagerClientInline,
    ]


@admin.register(SupportManager)
class SupportManagerAdmin(admin.ModelAdmin):
    list_display = ('name', 'second_name', 'email', 'phone_number', 'created_at')
    list_display_links = ('name', 'second_name')
    search_fields = ('name', 'second_name')
    ordering = ('name', 'second_name')
    list_per_page = 25

    fieldsets = [
        (None, {'fields': ['name', 'second_name', 'email', 'phone_number']}),
    ]

    inlines = [
        SupportManagerClientInline,
        SupportManagerDriverInline,
    ]


@admin.register(RepairReport)
class RepairReportAdmin(admin.ModelAdmin):
    list_display = [f.name for f in RepairReport._meta.fields]
    list_filter = ['numberplate', 'status_of_payment_repair']
    list_editable = ['status_of_payment_repair']
    search_fields = ['numberplate']
    list_per_page = 25


@admin.register(ServiceStation)
class ServiceStationAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'description')
    list_display_links = ('name',)
    list_filter = ['owner']
    search_fields = ('name', 'owner')
    ordering = ('name',)
    list_per_page = 25


@admin.register(ServiceStationManager)
class ServiceStationManagerAdmin(admin.ModelAdmin):
    list_display = ('name', 'second_name', 'service_station', 'email', 'phone_number', 'created_at')
    list_display_links = ('name', 'second_name')
    search_fields = ('name', 'second_name')
    ordering = ('name', 'second_name')
    list_per_page = 25

    fieldsets = [
        (None, {'fields': ['name', 'second_name', 'email', 'phone_number', 'service_station']}),
    ]

    inlines = [
        ServiceStationManagerVehicleInline,
        ServiceStationManagerFleetInline,
    ]


@admin.register(Report_of_driver_debt)
class ReportOfDriverDebtAdmin(admin.ModelAdmin):
    list_display = ('driver', 'image', 'created_at')
    list_filter = ('driver', 'created_at')
    search_fields = ('driver', 'created_at')

    fieldsets = [
        (None, {'fields': ['driver', 'image']}),
    ]


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('full_name_driver', 'event', 'event_date')
    list_filter = ('full_name_driver', 'event', 'event_date')

    fieldsets = [
        (None, {'fields': ['full_name_driver', 'event', 'chat_id', 'event_date']}),
    ]


@admin.register(Owner)
class OwnerAdmin(admin.ModelAdmin):
    list_display = ('name', 'second_name', 'email', 'phone_number', 'created_at')
    list_display_links = ('name', 'second_name')
    list_filter = ['created_at']
    search_fields = ('name', 'second_name')
    ordering = ('name', 'second_name')
    list_per_page = 25

    fieldsets = [
        (None, {'fields': ['name', 'second_name', 'email', 'phone_number', 'chat_id']}),
    ]


@admin.register(UseOfCars)
class UseofCarsAdmin(admin.ModelAdmin):
    list_display = [f.name for f in UseOfCars._meta.fields]


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name',
                    'email', 'password', 'phone_number',
                    'license_expired', 'admin_front',
                    'admin_back', 'admin_photo', 'admin_car_document',
                    'admin_insurance', 'insurance_expired',
                    'status_bolt', 'status_uklon']

    fieldsets = [
        (None, {'fields': ['first_name', 'last_name',
                           'email', 'phone_number',
                           'license_expired', 'driver_license_front',
                           'driver_license_back', 'photo', 'car_documents',
                           'insurance', 'insurance_expired'
                           ]}),
    ]


@admin.register(VehicleSpendings)
class VehicleSpendingsAdmin(admin.ModelAdmin):
    list_display = ['id', 'vehicle', 'amount', 'category', 'description']

    fieldsets = [
        (None, {'fields': ['vehicle', 'amount',
                           'category', 'description'
                           ]}),
    ]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.groups.filter(name='Investor').exists():
            investor_vehicles = Vehicle.objects.filter(investor_car__user=request.user)
            investor_vehicle_ids = investor_vehicles.values_list('licence_plate', flat=True)
            queryset = queryset.filter(vehicle__licence_plate__in=investor_vehicle_ids)
        return queryset


VehicleSpendingsAdmin = filter_queryset_by_group('Investor')(VehicleSpendingsAdmin)


@admin.register(TransactionsConversantion)
class TransactionsConversantionAdmin(admin.ModelAdmin):
    list_filter = ['vehicle']

    def get_list_display(self, request):
        if request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        else:
            return ['vehicle', 'sum_before_transaction', 'сurrency', 'currency_rate', 'sum_after_transaction']


@admin.register(CarEfficiency)
class CarEfficiencyAdmin(filter_queryset_by_group('Partner')(admin.ModelAdmin)):
    list_filter = ['licence_plate']

    def get_list_display(self, request):
        if request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        else:
            return ['total_kasa', 'licence_plate', 'efficiency', 'mileage', 'report_from']

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            ('Інформація по авто',          {'fields': ['licence_plate', 'total_kasa', 'efficiency',
                                                        'mileage']}),
            ('Додатково',                   {'fields': ['report_from'
                                                        ]}),
        ]

        return fieldsets


@admin.register(DriverEfficiency)
class DriverEfficiencyAdmin(filter_queryset_by_group('Partner')(admin.ModelAdmin)):
    list_filter = ['driver']

    def get_list_display(self, request):
        if request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        else:
            return ['driver', 'total_kasa', 'total_orders',
                    'efficiency', 'mileage', 'report_from',
                    'accept_percent', 'average_price']

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            ('Водій',                       {'fields': ['driver',
                                                        ]}),
            ('Інформація по водію',          {'fields': ['total_orders', 'total_kasa', 'efficiency',
                                                         'mileage', 'accept_percent', 'average_price']}),
            ('Додатково',                   {'fields': ['report_from'
                                                        ]}),
        ]

        return fieldsets


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['key', 'value', 'description', ]


@admin.register(BoltService)
class BoltServiceAdmin(admin.ModelAdmin):
    list_display = ['key', 'value', 'description', ]


@admin.register(UaGpsService)
class UaGpsServiceAdmin(admin.ModelAdmin):
    list_display = ['key', 'value', 'description', ]


@admin.register(NewUklonService)
class NewUklonServiceAdmin(admin.ModelAdmin):
    list_display = ['key', 'value', 'description', ]


@admin.register(UberService)
class UberServiceAdmin(admin.ModelAdmin):
    list_display = ['key', 'value', 'description', ]


@admin.register(RentInformation)
class RentInformationAdmin(filter_queryset_by_group('Partner')(admin.ModelAdmin)):
    list_filter = ('driver', 'created_at')

    def get_list_display(self, request):
        if request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        else:
            return ['id', 'driver_name', 'rent_time',
                    'rent_distance', 'created_at',
                    ]

    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
            fieldsets = [
                ('Водій',                       {'fields': ['driver_name',
                                                            ]}),
                ('Інформація про оренду',       {'fields': ['rent_time', 'rent_distance',
                                                            ]}),
                ('Додатково',                   {'fields': ['driver', 'partner',
                                                            ]}),
            ]

        else:
            fieldsets = [
                ('Водій',                       {'fields': ['driver_name',
                                                            ]}),
                ('Інформація про оренду',       {'fields': ['rent_time', 'rent_distance',
                                                            ]}),
            ]

        return fieldsets


@admin.register(Payments)
class PaymentsOrderAdmin(filter_queryset_by_group('Partner')(admin.ModelAdmin)):
    search_fields = ('vendor_name', 'full_name')
    list_filter = ('vendor_name', 'full_name')
    ordering = ('-report_from', 'full_name')
    list_per_page = 25

    def get_list_display(self, request):
        if request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        else:
            return ['id', 'report_from', 'vendor_name',
                    'driver_id', 'total_rides',
                    'total_distance', 'total_amount_cash',
                    'total_amount_on_card',
                    'total_amount', 'tips',
                    'bonuses', 'fares',
                    'fee', 'total_amount_without_fee',
                    'created_at', 'updated_at',
                    ]

    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
            fieldsets = [
                ('Інформація про звіт',         {'fields': ['report_from', 'vendor_name'
                                                            ]}),
                ('Інформація про водія',        {'fields': ['full_name', 'driver_id',
                                                            ]}),
                ('Інформація про поїздки',      {'fields': ['total_rides', 'total_distance',
                                                            ]}),
                ('Інформація про кошти',        {'fields': ['total_amount_cash',
                                                            'total_amount_on_card', 'total_amount',
                                                            'tips', 'bonuses', 'fares', 'fee',
                                                            'total_amount_without_fee',
                                                            ]}),
                ('Додатково',                   {'fields': ['partner',
                                                            ]}),
            ]

        else:
            fieldsets = [
                ('Інформація про звіт',         {'fields': ['report_from', 'vendor_name'
                                                            ]}),
                ('Інформація про водія',        {'fields': ['full_name', 'driver_id',
                                                            ]}),
                ('Інформація про поїздки',      {'fields': ['total_rides', 'total_distance',
                                                            ]}),
                ('Інформація про кошти',        {'fields': ['total_amount_cash',
                                                            'total_amount_on_card', 'total_amount',
                                                            'tips', 'bonuses', 'fares', 'fee',
                                                            'total_amount_without_fee',
                                                            ]}),
            ]
        return fieldsets


@admin.register(SummaryReport)
class SummaryReportAdmin(filter_queryset_by_group('Partner')(admin.ModelAdmin)):
    list_filter = ('full_name',)
    ordering = ('-report_from', 'full_name')
    list_per_page = 25

    def get_list_display(self, request):
        if request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        else:
            return ['id', 'report_from',
                    'full_name', 'total_rides',
                    'total_distance', 'total_amount_cash',
                    'total_amount_on_card',
                    'total_amount', 'tips',
                    'bonuses', 'fares',
                    'fee', 'total_amount_without_fee',
                    'created_at', 'updated_at',
                    ]

    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
            fieldsets = [
                ('Інформація про звіт',         {'fields': ['report_from',
                                                            ]}),
                ('Інформація про водія',        {'fields': ['full_name',
                                                            ]}),
                ('Інформація про поїздки',      {'fields': ['total_rides', 'total_distance',
                                                            ]}),
                ('Інформація про кошти',        {'fields': ['total_amount_cash',
                                                            'total_amount_on_card', 'total_amount',
                                                            'tips', 'bonuses', 'fares', 'fee',
                                                            'total_amount_without_fee',
                                                            ]}),
                ('Додатково',                   {'fields': ['partner',
                                                            ]}),
            ]

        else:
            fieldsets = [
                ('Інформація про звіт',         {'fields': ['report_from',
                                                            ]}),
                ('Інформація про водія',        {'fields': ['full_name',
                                                            ]}),
                ('Інформація про поїздки',      {'fields': ['total_rides', 'total_distance',
                                                            ]}),
                ('Інформація про кошти',        {'fields': ['total_amount_cash',
                                                            'total_amount_on_card', 'total_amount',
                                                            'tips', 'bonuses', 'fares', 'fee',
                                                            'total_amount_without_fee',
                                                            ]}),
            ]

        return fieldsets


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ('role',)
    list_per_page = 25

    fieldsets = [
        (None, {'fields': ['user', 'role']}),
    ]


@admin.register(Investor)
class InvestorAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'user', 'role')
    list_per_page = 25

    fieldsets = [
        (None, {'fields': ['phone_number', 'user', 'role']}),
    ]


@admin.register(Manager)
@add_partner_on_save_model(Manager)
class ManagerAdmin(filter_queryset_by_group('Partner')(admin.ModelAdmin)):
    search_fields = ('name', 'second_name')
    # ordering = ('name', 'second_name')
    list_per_page = 25

    def save_model(self, request, obj, form, change):
        obj.role = Role.DRIVER_MANAGER
        super().save_model(request, obj, form, change)

    def get_list_display(self, request):
        if request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        else:
            return ['id', 'name', 'second_name', 'email',
                    'phone_number', 'chat_id', 'created_at',
                    ]

    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
            fieldsets = [

                ('Додатково',                   {'fields': ['last_name', 'first_name', 'email', 'chat_id',
                                                            'phone_number', 'partner', 'user'
                                                            ]}),
            ]

        else:
            fieldsets = [
                ('Інформація про менеджера',    {'fields': ['last_name', 'first_name', 'email', 'chat_id',
                                                            'phone_number', 'partner', 'user'
                                                            ]}),
            ]

        return fieldsets

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'driver_id':
            kwargs['queryset'] = Driver.objects.filter(partner__user=request.user)

        return super().formfield_for_manytomany(db_field, request, **kwargs)


@admin.register(Driver)
@add_partner_on_save_model(Driver)
class DriverAdmin(filter_queryset_by_group('Partner')(admin.ModelAdmin)):
    search_fields = ('name', 'second_name')
    ordering = ('name', 'second_name')
    list_per_page = 25

    def has_add_permission(self, request):
        return False

    def get_list_display(self, request):
        if request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        else:
            return ['id', 'name', 'second_name',
                    'vehicle', 'phone_number', 'chat_id',
                    'schema', 'plan', 'rental',
                    'driver_status', 'manager', 'email',
                    'created_at',
                    ]

    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
            fieldsets = (
                ('Інформація про водія',        {'fields': ['name', 'second_name', 'email',
                                                            'phone_number',   'chat_id',
                                                            ]}),
                ('Тарифний план',               {'fields': ('schema', 'plan', 'rental', 'rate'
                                                            )}),
                ('Додатково',                   {'fields': ['partner', 'manager', 'vehicle', 'driver_status'
                                                            ]}),
            )

        else:
            fieldsets = (
                ('Інформація про водія',        {'fields': ['name', 'second_name', 'email',
                                                            'phone_number', 'chat_id',
                                                            ]}),
                ('Тарифний план',               {'fields': ('schema', 'plan', 'rental', 'rate'
                                                            )}),
                ('Додатково',                   {'fields': ['driver_status', 'manager',  'vehicle'
                                                            ]}),
            )

        return fieldsets

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            if db_field.name in ('manager', 'vehicle'):
                kwargs['queryset'] = db_field.related_model.objects.filter(partner__user=request.user)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        # Access the form fields using form.cleaned_data
        schema_field = form.cleaned_data.get('schema')

        if schema_field == 'HALF':
            obj.rate = 0.5
            obj.rental = obj.plan * obj.rate
        elif schema_field == 'RENT':
            obj.rate = 1
            obj.rental = int(obj.plan/2 - 400)
        fleet = Fleet.objects.get(name='Ninja')
        chat_id = form.cleaned_data.get('chat_id')
        driver_fleet = Fleets_drivers_vehicles_rate.objects.filter(fleet=fleet,
                                                                   driver_external_id=chat_id)
        if chat_id and not driver_fleet:
            Fleets_drivers_vehicles_rate.objects.create(fleet=fleet,
                                                        driver_external_id=chat_id,
                                                        driver=obj,
                                                        partner=obj.partner,
                                                        vehicle=obj.vehicle)

        super().save_model(request, obj, form, change)


@admin.register(Vehicle)
@add_partner_on_save_model(Vehicle)
class VehicleAdmin(filter_queryset_by_group('Partner')(admin.ModelAdmin)):
    search_fields = ('name', 'licence_plate', 'vin_code', 'gps_imei',)
    ordering = ('name',)
    exclude = ('deleted_at',)
    list_per_page = 25
    list_filter = ('manager',)

    def get_list_display(self, request):
        if request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        else:
            return ['id', 'name',
                    'licence_plate', 'type', 'vin_code',
                    'gps_imei', 'car_status', 'purchase_price',
                    'сurrency', 'investor_car', 'investor_percentage',
                    'currency_rate',
                    'сurrency_back', 'car_earnings',
                    'created_at',
                    ]

    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
            fieldsets = [
                ('Номер автомобіля',            {'fields': ['licence_plate',
                                                            ]}),
                ('Інформація про машину',       {'fields': ['name', 'type', 'purchase_price',
                                                            'сurrency', 'investor_car', 'investor_percentage',
                                                            'currency_rate', 'сurrency_back',
                                                            ]}),
                ('Особисті дані авто',          {'fields': ['vin_code', 'gps_imei', 'lat', 'lon',
                                                            'car_status', 'gps_id',
                                                            ]}),
                ('Додатково',                   {'fields': ['partner', 'manager',
                                                            ]}),
            ]

        else:
            fieldsets = [
                ('Номер автомобіля',            {'fields': ['licence_plate',
                                                            ]}),
                ('Інформація про машину',       {'fields': ['name', 'type', 'purchase_price',
                                                            'сurrency', 'investor_car', 'investor_percentage',
                                                            'currency_rate', 'сurrency_back',
                                                            ]}),
                ('Особисті дані авто',          {'fields': ['vin_code', 'gps_imei',
                                                            'car_status',
                                                            ]}),
                ('Додатково',                   {'fields': ['manager',
                                                            ]}),
            ]

        return fieldsets

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            if db_field.name == 'manager':
                kwargs['queryset'] = db_field.related_model.objects.filter(partner__user=request.user)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Order)
class OrderAdmin(filter_queryset_by_group('Partner')(admin.ModelAdmin)):
    def get_list_display(self, request):
        if request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        else:
            return ['id', 'from_address', 'to_the_address',
                    'phone_number', 'car_delivery_price',
                    'sum', 'payment_method', 'order_time',
                    'status_order', 'distance_gps',
                    'distance_google', 'driver', 'comment',
                    'created_at',
                    ]

    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
            fieldsets = [
                ('Адреси',                      {'fields': ['from_address', 'to_the_address',
                                                            ]}),
                ('Контакти',                    {'fields': ['phone_number', 'chat_id_client',
                                                            ]}),
                ('Ціни',                        {'fields': ['car_delivery_price', 'sum',
                                                            ]}),
                ('Деталі',                      {'fields': ['payment_method', 'order_time',
                                                            'status_order', 'distance_gps',
                                                            'distance_google', 'driver',
                                                            ]}),
            ]
        else:
            fieldsets = [
                ('Адреси',                      {'fields': ['from_address', 'to_the_address',
                                                            ]}),
                ('Контакти',                    {'fields': ['phone_number',
                                                            ]}),
                ('Ціни',                        {'fields': ['car_delivery_price', 'sum',
                                                            ]}),
                ('Деталі',                      {'fields': ['payment_method', 'order_time',
                                                            'status_order', 'distance_gps',
                                                            'distance_google', 'driver',
                                                            ]}),
            ]

        return fieldsets


@admin.register(FleetOrder)
class FleetOrderAdmin(filter_queryset_by_group('Partner')(admin.ModelAdmin)):
    list_filter = ('fleet', 'driver')

    def get_list_display(self, request):
        if request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        else:
            return ['order_id', 'fleet', 'driver', 'from_address', 'destination',
                    'accepted_time', 'finish_time',
                    'state'
                    ]

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            ('Адреси',                      {'fields': ['from_address', 'destination',
                                                        ]}),
            ('Інформація',                    {'fields': ['driver', 'fleet', 'state'
                                                          ]}),
            ('Час',                        {'fields': ['accepted_time', 'finish_time',
                                                       ]}),
        ]

        return fieldsets


@admin.register(Fleets_drivers_vehicles_rate)
@add_partner_on_save_model(Fleets_drivers_vehicles_rate)
class Fleets_drivers_vehicles_rateAdmin(filter_queryset_by_group('Partner')(admin.ModelAdmin)):
    list_filter = ('driver',)

    def get_list_display(self, request):
        if request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        else:
            return ['fleet', 'driver', 'vehicle',
                    'driver_external_id',
                    'created_at', 'pay_cash',
                    ]

    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
            fieldsets = [
                ('Деталі',                      {'fields': ['fleet', 'driver',
                                                            'vehicle', 'driver_external_id',
                                                            'pay_cash', 'partner',
                                                            ]}),
            ]
        else:
            fieldsets = [
                ('Деталі',                      {'fields': ['fleet', 'driver',
                                                            'vehicle', 'driver_external_id',
                                                            'pay_cash',
                                                            ]}),

            ]

        return fieldsets

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            if db_field.name == "vehicle":
                kwargs["queryset"] = Vehicle.objects.filter(partner__user=request.user)
            elif db_field.name == "driver":
                kwargs["queryset"] = Driver.objects.filter(partner__user=request.user)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Comment)
class CommentAdmin(filter_queryset_by_group('Partner')(admin.ModelAdmin)):

    def get_list_display(self, request):
        if request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        else:
            return ['comment', 'chat_id', 'processed',
                    ]

    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
            fieldsets = [
                ('Деталі',                      {'fields': ['comment', 'chat_id',
                                                            'processed', 'partner',
                                                            ]}),
            ]
        else:
            fieldsets = [
                ('Деталі',                      {'fields': ['comment', 'chat_id',
                                                            'processed', 'partner',
                                                            ]}),

            ]

        return fieldsets


@admin.register(ParkSettings)
class ParkSettingsAdmin(admin.ModelAdmin):

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            qs = qs.filter(partner__user=request.user)
        return qs

    def get_list_display(self, request):
        if request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        else:
            return ['description', 'value',
                    ]

    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
            fieldsets = [
                ('Деталі',                      {'fields': ['key', 'value',
                                                            'description', 'partner',
                                                            ]}),
            ]
        else:
            fieldsets = [
                ('Деталі',                      {'fields': ['description', 'value',
                                                            ]}),

            ]

        return fieldsets


@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        if request.method == "GET":
            user = request.user

            if user.groups.filter(name='Investor').exists():
                dashboard_url = reverse('dashboard_investor')
            elif user.groups.filter(name='Partner').exists():
                dashboard_url = reverse('dashboard_partner')
            elif user.groups.filter(name='Manager').exists():
                dashboard_url = reverse('dashboard')
            else:
                # Default dashboard for other users
                dashboard_url = reverse('dashboard')

            return redirect(dashboard_url)

        return super().changelist_view(request, extra_context)
