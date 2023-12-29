from django.contrib import admin
from django.contrib.auth.models import User as AuthUser
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldError
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.shortcuts import redirect
from django.db.models import Q
from polymorphic.admin import PolymorphicParentModelAdmin
from scripts.google_calendar import GoogleCalendar
from .filters import VehicleEfficiencyUserFilter, DriverEfficiencyUserFilter, RentInformationUserFilter, \
    TransactionInvestorUserFilter, ReportUserFilter, VehicleManagerFilter, SummaryReportUserFilter,\
    FleetRelatedFilter, ChildModelFilter
from .models import *


class SoftDeleteAdmin(admin.ModelAdmin):
    actions = ['delete_selected']

    def delete_selected(self, model, request, queryset):
        deleted = queryset
        for item in queryset:
            post_delete.send(sender=item.__class__, instance=item)
        deleted.update(deleted_at=timezone.localtime())

    def delete_view(self, request, object_id, extra_context=None):
        obj = self.get_object(request, object_id)
        if obj:
            obj.deleted_at = timezone.localtime()
            obj.save()
            post_delete.send(sender=obj.__class__, instance=obj)
        return redirect(f'admin:app_{self.model._meta.model_name}_changelist')

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions['delete_selected'] = (
            self.delete_selected, 'delete_selected', _(f"Видалити обрані {self.model._meta.verbose_name_plural}"))
        return actions

    def get_queryset(self, request):
        return super().get_queryset(request).exclude(deleted_at__isnull=False)


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
    model = FleetsDriversVehiclesRate
    extra = 0
    verbose_name = 'Fleets Drivers Vehicles Rate'
    verbose_name_plural = 'Fleets Drivers Vehicles Rate'

    fieldsets = [
        (None, {'fields': ['fleet', 'driver', 'vehicle', 'driver_external_id', 'rate']}),
    ]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name in ('vehicle', 'driver') and request.user.is_partner():
            kwargs['queryset'] = db_field.related_model.objects.filter(partner=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Fleet)
class FleetAdmin(admin.ModelAdmin):
    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Schema)
class SchemaAdmin(admin.ModelAdmin):
    list_display = ['title', 'schema']
    list_per_page = 25

    def save_model(self, request, obj, form, change):
        schema_field = form.cleaned_data.get('schema')
        calc_field = form.cleaned_data.get('salary_calculation')
        if calc_field == SalaryCalculation.WEEK:
            obj.shift_time = time.min
        if schema_field == 'HALF':
            obj.rate = 0.5
            obj.rental = obj.plan * obj.rate
        elif schema_field == 'RENT':
            obj.rate = 1
        else:
            obj.rental = obj.plan * (1 - obj.rate)
        if request.user.is_partner():
            obj.partner_id = request.user.pk
        super().save_model(request, obj, form, change)

    def get_fieldsets(self, request, obj=None):
        if request.user.is_partner():
            fieldsets = [
                ('Деталі', {'fields': ['title', 'schema', 'rate', 'plan', 'rental', 'rent_price', 'limit_distance',
                                       'shift_time', 'salary_calculation']}),
            ]
            return fieldsets
        return super().get_fieldsets(request)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_partner():
            queryset = queryset.filter(partner=request.user)
        elif request.user.is_manager():
            manager = Manager.objects.get(pk=request.user.pk)
            queryset = queryset.filter(partner=manager.managers_partner)
        return queryset


@admin.register(DriverSchemaRate)
class DriverRateLevelsAdmin(admin.ModelAdmin):
    list_display = ['period', 'threshold', 'rate']
    list_per_page = 25
    list_filter = ("period",)

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            (None, {'fields': ['period', 'threshold', 'rate']}),
        ]
        return fieldsets

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_partner():
            queryset = queryset.filter(partner=request.user)
        return queryset

    def save_model(self, request, obj, form, change):
        if request.user.is_partner():
            obj.partner_id = request.user.pk
        super().save_model(request, obj, form, change)


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
    list_display = ('name', 'second_name', 'email', 'chat_id', 'phone_number', 'role', 'created_at')
    list_display_links = ('name', 'second_name')
    list_filter = ['created_at', 'role']
    search_fields = ('name', 'second_name')
    ordering = ('name', 'second_name')
    list_per_page = 25

    fieldsets = [
        (None, {'fields': ['name', 'second_name', 'email', 'chat_id', 'role', 'phone_number']}),
    ]


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'second_name', 'email', 'chat_id', 'phone_number', 'created_at')
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


@admin.register(ReportDriveDebt)
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


@admin.register(UseOfCars)
class UseOfCarsAdmin(admin.ModelAdmin):
    list_display = [f.name for f in UseOfCars._meta.fields]
    list_per_page = 25


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


@admin.register(VehicleSpending)
class VehicleSpendingAdmin(admin.ModelAdmin):
    list_display = ['id', 'vehicle', 'amount', 'category', 'description']

    fieldsets = [
        (None, {'fields': ['vehicle', 'amount',
                           'category', 'description'
                           ]}),
    ]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        user = request.user
        if user.is_investor():
            filter_condition = Q(vehicle__investor_car=user)
        elif user.is_manager():
            filter_condition = Q(vehicle__manager=user)
        elif user.is_partner():
            filter_condition = Q(vehicle__partner=user)
        else:
            filter_condition = Q()

        queryset = queryset.filter(filter_condition)

        return queryset

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        user = request.user
        if not user.is_superuser:
            if db_field.name == 'vehicle':

                if user.is_partner():
                    kwargs['queryset'] = db_field.related_model.objects.filter(partner=request.user)
                if user.is_manager():
                    kwargs['queryset'] = db_field.related_model.objects.filter(manager=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(InvestorPayments)
class TransactionsConversationAdmin(admin.ModelAdmin):
    list_filter = (TransactionInvestorUserFilter, )

    def get_list_display(self, request):
        if request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        else:
            return ['vehicle', 'sum_before_transaction', 'currency', 'currency_rate', 'sum_after_transaction']


@admin.register(CarEfficiency)
class CarEfficiencyAdmin(admin.ModelAdmin):
    list_filter = (VehicleEfficiencyUserFilter, )
    list_per_page = 25
    raw_id_fields = ['vehicle']
    list_select_related = ['vehicle']

    def get_list_display(self, request):
        if request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        else:
            return ['report_from', 'vehicle', 'total_kasa',
                    'total_spending', 'efficiency', 'mileage']

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            ('Інформація по авто',          {'fields': ['report_from', 'vehicle', 'total_kasa',
                                                        'total_spending', 'efficiency',
                                                        'mileage']}),
        ]

        return fieldsets

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_partner():
            qs = qs.filter(partner=request.user)
        elif request.user.is_manager():
            qs = qs.filter(vehicle__manager=request.user)
        return qs


@admin.register(DriverEfficiency)
class DriverEfficiencyAdmin(admin.ModelAdmin):
    list_filter = [DriverEfficiencyUserFilter]
    list_per_page = 25
    raw_id_fields = ['driver', 'partner']
    list_select_related = ['driver', 'partner']

    def get_list_display(self, request):
        if request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        else:
            return ['report_from', 'driver', 'total_kasa',
                    'efficiency', 'average_price', 'mileage',
                    'total_orders', 'accept_percent', 'road_time']

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            ('Водій',                       {'fields': ['report_from', 'driver',
                                                        ]}),
            ('Інформація по водію',          {'fields': ['total_kasa', 'average_price', 'efficiency',
                                                         'mileage']}),
            ('Додатково',                   {'fields': ['total_orders', 'accept_percent', 'road_time'
                                                        ]}),
        ]

        return fieldsets

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_partner():
            return qs.filter(partner=request.user)
        if request.user.is_manager():
            return qs.filter(driver__manager=request.user)
        return qs


@admin.register(Service)
class ServiceAdmin(PolymorphicParentModelAdmin):
    base_model = Service
    child_models = (UberService, UaGpsService, NewUklonService, BoltService)
    list_display = ['key', 'value', 'description', ]
    list_filter = [ChildModelFilter]


@admin.register(RentInformation)
class RentInformationAdmin(admin.ModelAdmin):
    list_filter = (RentInformationUserFilter, 'created_at')
    list_per_page = 25
    raw_id_fields = ['driver', 'partner']
    list_select_related = ['partner', 'driver']

    def get_list_display(self, request):
        if request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        else:
            return ['report_from', 'driver', 'rent_distance',
                    ]

    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
            fieldsets = [
                ('Водій',                       {'fields': ['driver',
                                                            ]}),
                ('Інформація про оренду',       {'fields': ['report_from', 'rent_distance',
                                                            ]}),
                ('Додатково',                   {'fields': ['partner',
                                                            ]}),
            ]

        else:
            fieldsets = [
                ('Водій',                       {'fields': ['driver',
                                                            ]}),
                ('Інформація про оренду',       {'fields': ['report_from', 'rent_distance',
                                                            ]}),
            ]

        return fieldsets

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_partner():
            return qs.filter(partner=request.user)
        if request.user.is_manager():
            return qs.filter(driver__manager=request.user)
        return qs


@admin.register(Payments)
class PaymentsOrderAdmin(admin.ModelAdmin):
    search_fields = ('vendor_name', 'full_name')
    list_filter = ('vendor_name', ReportUserFilter)
    ordering = ('-report_from', 'full_name')
    list_per_page = 25
    raw_id_fields = ['vehicle', 'partner']
    list_select_related = ['vehicle', 'partner']

    def get_list_display(self, request):
        if request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        else:
            return ['report_from', 'report_to', 'vendor_name', 'full_name',
                    'total_amount_without_fee', 'total_amount_cash', 'total_amount_on_card',
                    'total_distance', 'total_rides',
                    ]

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            ('Інформація про звіт', {'fields': ['report_from', 'report_to', 'vendor_name'
                                                ]}),
            ('Інформація про водія', {'fields': ['full_name',
                                                 ]}),
            ('Інформація про кошти', {'fields': ['total_amount_cash',
                                                 'total_amount_on_card', 'total_amount',
                                                 'tips', 'bonuses', 'fares', 'fee',
                                                 'total_amount_without_fee',
                                                 ]}),
            ('Інформація про поїздки', {'fields': ['total_rides', 'total_distance',
                                                   ]})]
        if request.user.is_superuser:
            fieldsets.append(('Додатково',                   {'fields': ['partner']}))

        return fieldsets

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_partner():
            qs = qs.filter(partner=request.user)
        if request.user.is_manager():
            manager_drivers = Driver.objects.filter(manager=request.user)
            full_names = [f"{driver.name} {driver.second_name}" for driver in manager_drivers]
            return qs.filter(full_name__in=full_names)
        return qs


@admin.register(SummaryReport)
class SummaryReportAdmin(admin.ModelAdmin):
    list_filter = (SummaryReportUserFilter,)
    ordering = ('-report_from', 'driver')
    list_per_page = 25
    raw_id_fields = ['driver', 'partner', 'vehicle']
    list_select_related = ['vehicle', 'driver', 'partner']

    def get_list_display(self, request):
        if request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        else:
            return ['report_from', 'report_to',
                    'driver', 'total_amount_without_fee', 'total_amount_cash',
                    'total_amount_on_card', 'total_distance', 'total_rides',
                    ]

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            ('Інформація про звіт', {'fields': ['report_from', 'report_to',
                                                ]}),
            ('Інформація про водія', {'fields': ['driver',
                                                 ]}),
            ('Інформація про кошти', {'fields': ['total_amount_cash',
                                                 'total_amount_on_card', 'total_amount',
                                                 'tips', 'bonuses', 'fares', 'fee',
                                                 'total_amount_without_fee',
                                                 ]}),
            ('Інформація про поїздки', {'fields': ['total_rides', 'total_distance',
                                                   ]})]
        if request.user.is_superuser:
            fieldsets.append(('Додатково', {'fields': ['partner']}))

        return fieldsets

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_partner():
            qs = qs.filter(partner=request.user)
        if request.user.is_manager():
            manager_drivers = Driver.objects.filter(manager=request.user)
            return qs.filter(driver__in=manager_drivers)
        return qs


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ('username', 'chat_id', 'gps_url', 'contacts')
    list_per_page = 25

    fieldsets = [
        ('Інформація про власника', {'fields': ['email', 'password', 'first_name', 'last_name', 'chat_id',
                                                'gps_url', 'contacts']}),
    ]

    def save_model(self, request, obj, form, change):
        if not change:
            user = Partner.objects.create_user(
                username=obj.email,
                password=obj.password,
                role=Role.PARTNER,
                is_staff=True,
                is_active=True,
                is_superuser=False,
                first_name=obj.first_name,
                last_name=obj.last_name,
                email=obj.email,
                contacts=obj.contacts,
                gps_url=obj.gps_url
            )
            user.groups.add(Group.objects.get(name='Partner'))
            gc = GoogleCalendar()
            cal_id = gc.create_calendar()
            user.calendar = cal_id
            permissions = gc.add_permission(obj.email)
            gc.service.acl().insert(calendarId=cal_id, body=permissions).execute()
            user.save()
        else:
            super().save_model(request, obj, form, change)


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_per_page = 25


@admin.register(Investor)
class InvestorAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name')
    list_per_page = 25

    def save_model(self, request, obj, form, change):
        if not change:
            user = Investor.objects.create_user(
                username=obj.email,
                password=obj.password,
                role=Role.INVESTOR,
                is_staff=True,
                is_active=True,
                is_superuser=False,
                first_name=obj.first_name,
                last_name=obj.last_name,
                phone_number=obj.phone_number,
                email=obj.email
            )
            user.groups.add(Group.objects.get(name='Investor'))
            if request.user.is_partner():
                user.investors_partner_id = request.user.pk
                user.save()
        else:
            super().save_model(request, obj, form, change)

    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
            fieldsets = [
                ('Інформація про інвестора',
                 {'fields': ['email', 'password',
                             'last_name', 'first_name',
                             'phone_number', 'investors_partner']}),
            ]
            return fieldsets
        if obj:
            fieldsets = [
                ('Інформація про інвестора',
                 {'fields': ['email', 'last_name', 'first_name', 'phone_number']}),
            ]
        else:
            fieldsets = [
                ('Інформація про інвестора',
                 {'fields': ['email', 'password', 'last_name', 'first_name', 'phone_number']}),
            ]

        return fieldsets

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_partner():
            return qs.filter(investors_partner=request.user)
        return qs


@admin.register(Manager)
class ManagerAdmin(admin.ModelAdmin):
    search_fields = ('first_name', 'last_name')
    list_per_page = 25

    def save_model(self, request, obj, form, change):
        if not change:
            user = Manager.objects.create_user(
                username=obj.email,
                password=obj.password,
                role=Role.DRIVER_MANAGER,
                is_staff=True,
                is_active=True,
                is_superuser=False,
                first_name=obj.first_name,
                last_name=obj.last_name,
                phone_number=obj.phone_number,
                chat_id=obj.chat_id,
                email=obj.email
            )
            user.groups.add(Group.objects.get(name='Manager'))
            if request.user.is_partner():
                user.managers_partner_id = request.user.pk
                user.save()
        else:
            super().save_model(request, obj, form, change)

    def get_list_display(self, request):
        if request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        else:
            return ['first_name', 'last_name', 'email', 'phone_number', 'chat_id']

    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
            fieldsets = [
                ('Інформація про менеджера',
                 {'fields': ['email', 'last_name', 'first_name',
                             'chat_id', 'phone_number', 'managers_partner',
                             ]}),
            ]
            return fieldsets
        if obj:
            fieldsets = [
                ('Інформація про менеджера',
                 {'fields': ['email', 'last_name', 'first_name', 'chat_id', 'phone_number']}),
            ]

        else:
            fieldsets = [
                ('Інформація про менеджера',
                 {'fields': ['email', 'password', 'last_name', 'first_name', 'chat_id', 'phone_number']}),
            ]

        return fieldsets

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'driver_id':
            kwargs['queryset'] = Driver.objects.filter(partner=request.user)

        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_partner():
            return qs.filter(managers_partner=request.user)
        return qs


@admin.register(Driver)
class DriverAdmin(SoftDeleteAdmin):
    search_fields = ('name', 'second_name')
    ordering = ('name', 'second_name')
    list_display_links = ('name', 'second_name')
    list_per_page = 25
    readonly_fields = ('name', 'second_name', 'email', 'phone_number', 'driver_status')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_partner():
            return qs.filter(partner=request.user).select_related('schema', 'manager')
        if request.user.is_manager():
            return qs.filter(manager=request.user).select_related('schema')
        return qs

    def get_list_editable(self, request):
        if request.user.is_partner():
            return ['schema', 'manager']
        elif request.user.is_manager():
            return ['schema']

    def changelist_view(self, request, extra_context=None):
        self.list_editable = self.get_list_editable(request)
        return super().changelist_view(request, extra_context)

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields if not request.user.is_superuser else tuple()

    def get_list_display(self, request):
        if request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        elif request.user.is_partner():
            return ['name', 'second_name',
                    'vehicle', 'manager', 'chat_id',
                    'driver_status', 'schema',
                    'created_at',
                    ]
        else:
            return ['name', 'second_name',
                    'vehicle', 'chat_id', 'schema',
                    'driver_status'
                    ]

    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
            fieldsets = (
                ('Інформація про водія',        {'fields': ['name', 'second_name', 'email',
                                                            'phone_number',   'chat_id',
                                                            ]}),
                ('Тарифний план',               {'fields': ('schema',
                                                            )}),
                ('Додатково',                   {'fields': ['partner', 'manager', 'vehicle', 'driver_status'
                                                            ]}),
            )

        elif request.user.is_partner():
            fieldsets = (
                ('Інформація про водія',        {'fields': ['name', 'second_name', 'email',
                                                            'phone_number', 'chat_id',
                                                            ]}),
                ('Тарифний план',               {'fields': ('schema',
                                                            )}),
                ('Додатково',                   {'fields': ['driver_status', 'manager',  'vehicle'
                                                            ]}),
            )
        else:
            fieldsets = (
                ('Інформація про водія',        {'fields': ['name', 'second_name', 'email',
                                                            'phone_number', 'chat_id',
                                                            ]}),
                ('Тарифний план',               {'fields': ('schema',
                                                            )}),
                ('Додатково',                   {'fields': ['driver_status', 'vehicle'
                                                            ]}),
            )
        return fieldsets

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if request.user.is_partner():
            if db_field.name in ('vehicle', 'schema'):
                kwargs['queryset'] = db_field.related_model.objects.filter(partner=request.user)
            if db_field.name == 'manager':
                kwargs['queryset'] = db_field.related_model.objects.filter(managers_partner=request.user)
        if request.user.is_manager():
            if db_field.name == 'vehicle':
                kwargs['queryset'] = db_field.related_model.objects.filter(manager=request.user)
            if db_field.name == 'schema':
                manager = Manager.objects.get(pk=request.user.pk)
                kwargs['queryset'] = db_field.related_model.objects.filter(
                    partner=manager.managers_partner.pk).select_related('partner')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        fleet = Fleet.objects.get(name='Ninja')
        chat_id = form.cleaned_data.get('chat_id')
        driver_fleet = FleetsDriversVehiclesRate.objects.filter(fleet=fleet,
                                                                driver_external_id=chat_id)
        if chat_id and not driver_fleet:
            FleetsDriversVehiclesRate.objects.create(fleet=fleet,
                                                     driver_external_id=chat_id,
                                                     driver=obj,
                                                     partner=obj.partner,
                                                     )

        super().save_model(request, obj, form, change)


@admin.register(FiredDriver)
class FiredDriverAdmin(admin.ModelAdmin):

    def get_model_perms(self, request):
        perms = super().get_model_perms(request)
        if request.user.is_partner():
            perms.update(view=True, change=True, add=True, delete=True)
        return perms

    def get_queryset(self, request):
        qs = super().get_queryset(request).filter(deleted_at__isnull=False)
        if request.user.is_partner():
            return qs.filter(partner_id=request.user.pk)
        return qs

    change_form_template = 'admin/change_form_fired_driver.html'

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}

        if 'restore_driver' in request.POST:
            # Add your custom restore logic here
            instance = self.get_object(request, object_id)
            if instance:
                instance.deleted_at = None
                instance.save()

                self.message_user(request, 'Object restored successfully.')

                # Redirect to the change form again
                list_url = reverse('admin:app_fireddriver_changelist')
                return HttpResponseRedirect(list_url)

        return super().change_view(request, object_id, form_url, extra_context)


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    search_fields = ('name', 'licence_plate', 'vin_code',)
    ordering = ('name',)
    exclude = ('deleted_at',)
    list_display_links = ('licence_plate',)
    list_per_page = 10
    list_filter = (VehicleManagerFilter,)
    readonly_fields = ('licence_plate',)

    def get_list_display(self, request):
        if request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        elif request.user.is_partner():
            return ['licence_plate', 'name',
                    'vin_code', 'gps',
                    'purchase_price',
                    'manager', 'investor_car', 'created_at'
                    ]
        else:
            return ['licence_plate', 'name',
                    'vin_code', 'gps',
                    'purchase_price'
                    ]

    def get_list_editable(self, request):
        if request.user.is_partner():
            return ['investor_car', 'manager', 'purchase_price', 'gps']
        elif request.user.is_manager():
            return ['gps']
        else:
            return []

    def changelist_view(self, request, extra_context=None):
        self.list_editable = self.get_list_editable(request)
        return super().changelist_view(request, extra_context)

    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
            fieldsets = [
                ('Номер автомобіля',            {'fields': ['licence_plate',
                                                            ]}),
                ('Інформація про машину',       {'fields': ['name', 'purchase_price',
                                                            'currency', 'investor_car', 'investor_percentage',
                                                            'currency_rate', 'currency_back',
                                                            ]}),
                ('Особисті дані авто',          {'fields': ['vin_code', 'gps_imei', 'lat', 'lon',
                                                            'car_status', 'gps',
                                                            ]}),
                ('Додатково',                   {'fields': ['chat_id', 'partner', 'manager',
                                                            ]}),
            ]

        elif request.user.is_partner():
            fieldsets = (
                ('Номер автомобіля',            {'fields': ['licence_plate', 'gps_imei', 'gps',
                                                            ]}),
                ('Інформація про машину',       {'fields': ['name', 'purchase_price',
                                                            'investor_car', 'investor_percentage'
                                                            ]}),
                ('Додатково',                   {'fields': ['manager',
                                                            ]}),
            )
        elif request.user.is_manager():
            fieldsets = (
                ('Номер автомобіля',            {'fields': ['licence_plate', 'gps_imei', 'gps',
                                                            ]}),
                ('Інформація про машину',       {'fields': ['name', 'purchase_price',
                                                            ]}),
            )
        else:
            fieldsets = (
                ('Номер автомобіля',            {'fields': ['licence_plate', 'gps_imei',
                                                            ]}),
                ('Інформація про машину',       {'fields': ['name', 'purchase_price',
                                                            ]}),
            )
        return fieldsets

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        filter_mapping = {
            'investor_car': 'investors_partner',
            'manager': 'managers_partner',
            'gps': 'partner',
        }
        if request.user.is_partner():
            related_field_name = filter_mapping.get(db_field.name)
            if related_field_name:
                filter_param = {related_field_name: request.user}
                kwargs['queryset'] = db_field.related_model.objects.filter(
                    **filter_param).select_related(related_field_name)
        elif request.user.is_manager():
            if db_field.name == 'gps':
                manager = Manager.objects.get(pk=request.user.pk)
                kwargs['queryset'] = db_field.related_model.objects.filter(partner=manager.managers_partner.pk).select_related('partner')

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_manager():
            return qs.filter(manager=request.user).select_related('gps')
        if request.user.is_partner():
            return qs.filter(partner=request.user).select_related('gps', 'manager', 'investor_car')
        if request.user.is_investor():
            return qs.filter(investor_car=request.user)
        return qs


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
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
class FleetOrderAdmin(admin.ModelAdmin):
    list_filter = ('fleet', 'driver')
    list_per_page = 25
    raw_id_fields = ['vehicle', 'driver', 'partner']
    list_select_related = ['vehicle', 'driver', 'partner']

    def get_list_display(self, request):
        if request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        else:
            return ['order_id', 'fleet', 'driver', 'from_address', 'destination',
                    'accepted_time', 'finish_time',
                    'state', 'payment', 'price', 'vehicle_id'
                    ]

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            ('Адреси',                      {'fields': ['from_address', 'destination',
                                                        ]}),
            ('Інформація',                    {'fields': ['driver', 'fleet', 'state'
                                                          ]}),
            ('Час',                        {'fields': ['accepted_time', 'finish_time',
                                                       ]}),
            ('Ціна',                        {'fields': ['price', 'payment', 'tips',
                                ]}),
        ]

        return fieldsets


@admin.register(FleetsDriversVehiclesRate)
class FleetsDriversVehiclesRateAdmin(admin.ModelAdmin):
    list_filter = (FleetRelatedFilter,)
    readonly_fields = ('fleet', 'driver_external_id')
    list_per_page = 25
    list_select_related = ['driver', 'partner']

    def get_list_display(self, request):
        if request.user.is_partner() or request.user.is_manager():
            return ('fleet', 'driver',
                    'driver_external_id',
                    )
        return [f.name for f in self.model._meta.fields]

    def get_fieldsets(self, request, obj=None):
        if request.user.is_partner() or request.user.is_manager():
            fieldsets = [
                ('Деталі',                      {'fields': ['fleet', 'driver',
                                                            'driver_external_id',
                                                            ]}),
            ]

            return fieldsets
        return super().get_fieldsets(request)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "driver":
            if request.user.is_partner():
                kwargs["queryset"] = Driver.objects.get_active(partner=request.user)
            if request.user.is_manager():
                kwargs["queryset"] = Driver.objects.get_active(manager=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_partner():
            return qs.filter(partner=request.user)
        elif request.user.is_manager():
            manager = Manager.objects.get(pk=request.user.pk)
            return qs.filter(partner=manager.managers_partner)
        return qs


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):

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
            qs = qs.filter(partner=request.user)
        return qs

    def get_list_display(self, request):
        if request.user.is_partner():
            return ['description', 'value']
        return [f.name for f in self.model._meta.fields]

    def get_fieldsets(self, request, obj=None):
        if request.user.is_partner():
            fieldsets = [
                ('Деталі',                      {'fields': ['description', 'value',
                                                            ]}),

            ]

            return fieldsets
        return super().get_fieldsets(request)


@admin.register(TaskScheduler)
class TaskSchedulerAdmin(admin.ModelAdmin):
    list_display = ['name', 'task_time', 'periodic', 'arguments']
    list_editable = ['task_time', 'periodic']

    def get_fieldsets(self, request, obj=None):

        fieldsets = [
            ('Деталі', {'fields': ['name', 'task_time', 'periodic', 'weekly', 'interval', 'arguments'
                                   ]}),

        ]

        return fieldsets
