from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.shortcuts import redirect
from django.db.models import Prefetch
from django_celery_beat.models import PeriodicTask
from polymorphic.admin import PolymorphicParentModelAdmin
from scripts.google_calendar import GoogleCalendar
from .filters import VehicleEfficiencyUserFilter, DriverEfficiencyUserFilter, RentInformationUserFilter, \
    TransactionInvestorUserFilter, ReportUserFilter, VehicleManagerFilter, SummaryReportUserFilter, \
    ChildModelFilter, PartnerPaymentFilter, FleetFilter, FleetDriverFilter, FleetOrderFilter, VehicleSpendingFilter
from .models import *
from .ninja_sync import NinjaFleet
from .utils import get_schedule


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
            self.delete_selected, 'delete_selected', _(f"Приховати {self.model._meta.verbose_name_plural}"))
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


class SchemaForm(forms.ModelForm):
    drivers = forms.ModelMultipleChoiceField(
        queryset=Driver.objects.none(),
        required=False,
        widget=FilteredSelectMultiple('Водії', False)
    )

    class Meta:
        model = Schema
        fields = ('title', 'salary_calculation', 'schema', 'shift_time', 'plan', 'cash', 'rate',
                  'rental', 'rent_price', 'limit_distance', 'drivers')


@admin.register(Schema)
class SchemaAdmin(admin.ModelAdmin):
    list_display = ('title', 'salary_calculation')
    search_fields = ('title',)

    def get_list_filter(self, request):
        list_filter = []
        if request.user.is_superuser:
            list_filter.append('partner')
        return list_filter

    def save_model(self, request, obj, form, change):
        schema_field = form.cleaned_data.get('schema')
        calc_field = form.cleaned_data.get('salary_calculation')

        if calc_field == SalaryCalculation.WEEK:
            obj.shift_time = time.min

        old_obj = Schema.objects.filter(pk=obj.pk).first()
        if old_obj:
            old_shift_time = old_obj.shift_time
            if obj.shift_time != old_shift_time:
                crontab = get_schedule(obj.shift_time)
                old_crontab = get_schedule(old_shift_time)
                if calc_field == SalaryCalculation.WEEK:
                    crontab = get_schedule(time(9, 0))
                elif old_obj.salary_calculation == SalaryCalculation.WEEK:
                    old_crontab = get_schedule(time(9, 0))

                new_task, created = PeriodicTask.objects.get_or_create(
                    name=f"get_information_from_fleets({request.user.pk}_{crontab})",
                    task="auto.tasks.get_information_from_fleets",
                    queue=f"beat_tasks_{request.user.pk}",
                    crontab=crontab,
                    defaults={"args": f"[{request.user.pk}, [{obj.pk}]]"})
                if not created:
                    new_args = eval(new_task.args)
                    new_args[1].append(obj.pk)
                    new_task.args = str(new_args)
                    new_task.save(update_fields=["args"])
                old_task = PeriodicTask.objects.filter(
                    name=f"get_information_from_fleets({request.user.pk}_{old_crontab})")
                if old_task.exists():
                    task = old_task.first()
                    old_args = eval(task.args)
                    old_args[1] = [value for value in old_args[1] if value != obj.pk]
                    if old_args[1]:
                        task.args = str(old_args)
                        task.save(update_fields=["args"])
                    else:
                        task.delete()
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

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = SchemaForm
        base_queryset = Driver.objects.filter(Q(schema__isnull=True) | Q(schema=obj),
                                              deleted_at__isnull=True)
        initial_queryset = Driver.objects.get_active(schema=obj)
        if request.user.is_partner():
            form.base_fields['drivers'].queryset = base_queryset.filter(partner=request.user)
            form.base_fields['drivers'].initial = initial_queryset.filter(partner=request.user)
        elif request.user.is_manager():
            form.base_fields['drivers'].queryset = base_queryset.filter(manager=request.user)
            form.base_fields['drivers'].initial = initial_queryset.filter(manager=request.user)
        else:
            form.base_fields['drivers'].queryset = base_queryset
            form.base_fields['drivers'].initial = initial_queryset
        return form

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        if 'drivers' in form.cleaned_data:
            form.instance.driver_set.set(form.cleaned_data['drivers'])

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

    def get_list_filter(self, request):
        list_filter = ["period"]
        if request.user.is_superuser:
            list_filter.insert(0, 'partner')
        return list_filter

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
    list_display = ('id', 'vehiclegps')
    list_display_links = ('id',)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        queryset = queryset.select_related('vehiclegps').only('id', 'vehiclegps')

        return queryset


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
    ordering = ('second_name', 'name')
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
    list_display = ['vehicle', 'amount', 'spending_category', 'description', 'display_photo', 'created_date']
    list_filter = (VehicleSpendingFilter, 'spending_category', 'created_at')
    readonly_fields = ('display_photo',)

    class Media:
        css = {
            'all': ('https://cdnjs.cloudflare.com/ajax/libs/lightbox2/2.11.3/css/lightbox.min.css',)
        }
        js = (
            'https://code.jquery.com/jquery-3.6.4.min.js',
            'https://cdnjs.cloudflare.com/ajax/libs/lightbox2/2.11.3/js/lightbox.min.js',
        )

    def get_fieldsets(self, request, obj=None):

        if obj:
            fieldsets = [
                ('Інформація про витрату', {'fields': ['amount', 'description']}),
                ('Фото', {'fields': ['photo', 'display_photo']})
            ]
        else:
            fieldsets = [
                ('Інформація про витрату', {'fields': ['vehicle', 'spending_category', 'amount', 'description']}),
                ('Фото', {'fields': ['photo', 'display_photo']})
            ]

        return fieldsets

    def display_photo(self, obj):
        if obj.photo:
            url = obj.photo.url
            return mark_safe(f'<a href="{url}" data-lightbox="image"><img src="{url}" width="200" height="150"></a>')

    def created_date(self, obj):
        return obj.created_at.date()

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        user = request.user
        if user.is_investor():
            filter_condition = Q(vehicle__investor_car=user)
        elif user.is_manager():
            filter_condition = Q(vehicle__manager=user)
        elif user.is_partner():
            filter_condition = Q(partner=user)
        else:
            filter_condition = Q()

        queryset = queryset.filter(filter_condition).select_related('vehicle', 'partner', 'vehicle__manager')

        return queryset

    def save_model(self, request, obj, form, change):
        if request.user.is_partner():
            obj.partner_id = request.user.pk
        if request.user.is_manager():
            obj.partner = request.user.manager.managers_partner
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        user = request.user
        if not user.is_superuser:
            if db_field.name == 'vehicle':

                if user.is_partner():
                    kwargs['queryset'] = db_field.related_model.objects.get_active(partner=user)
                if user.is_manager():
                    kwargs['queryset'] = db_field.related_model.objects.get_active(manager=user)
            if db_field.name == 'spending_category':
                if user.is_partner():
                    kwargs['queryset'] = db_field.related_model.objects.filter(Q(partner=user))
                if user.is_manager():
                    manager = Manager.objects.get(pk=request.user.pk)
                    kwargs['queryset'] = db_field.related_model.objects.filter(partner=manager.managers_partner)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    display_photo.short_description = 'Попередній перегляд'
    created_date.short_description = 'Дата створення'


@admin.register(InvestorPayments)
class TransactionsConversationAdmin(admin.ModelAdmin):
    list_filter = (TransactionInvestorUserFilter,)

    def get_list_display(self, request):
        display = ['report_from', 'report_to', 'vehicle', 'earning',
                   'investor', 'status', 'currency', 'currency_rate', 'sum_after_transaction']
        if request.user.is_superuser:
            display.append('partner')
        return display

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_partner():
            return qs.filter(partner=request.user)
        return qs.select_related('vehicle', 'investor', 'partner')


@admin.register(PartnerEarnings)
class PartnerEarningsAdmin(admin.ModelAdmin):

    def get_list_display(self, request):
        display = ['report_from', 'report_to', 'driver', 'vehicle', 'earning']
        if request.user.is_superuser:
            display.append('partner')
        return display

    def get_list_filter(self, request):
        list_filter = [PartnerPaymentFilter]
        if request.user.is_superuser:
            list_filter = ['partner', 'driver'] + list_filter
        return list_filter

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related('partner').prefetch_related(
            Prefetch('driver', queryset=Driver.objects.only('name', 'second_name')),
            Prefetch('vehicle', queryset=Vehicle.objects.only('licence_plate'))
        )
        if request.user.is_partner():
            qs = qs.filter(partner=request.user)
        return qs

@admin.register(CarEfficiency)
class CarEfficiencyAdmin(admin.ModelAdmin):
    list_per_page = 25

    def get_list_filter(self, request):
        list_filter = [VehicleEfficiencyUserFilter]
        if request.user.is_superuser:
            list_filter.insert(0, 'partner')
        return list_filter

    def get_list_display(self, request):
        if request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        else:
            return ['report_from', 'vehicle', 'total_kasa',
                    'total_spending', 'efficiency', 'mileage']

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            ('Інформація по авто', {'fields': ['report_from', 'vehicle', 'total_kasa',
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
        return qs.select_related('vehicle', 'partner', 'investor')


@admin.register(DriverEfficiency)
class DriverEfficiencyAdmin(admin.ModelAdmin):
    list_per_page = 25
    raw_id_fields = ['driver', 'partner']
    list_select_related = ['driver', 'partner']

    def get_list_filter(self, request):
        list_filter = [DriverEfficiencyUserFilter]
        if request.user.is_superuser:
            list_filter.insert(0, 'partner')
        return list_filter

    def get_list_display(self, request):
        if request.user.is_superuser:
            return ['report_from', 'report_to', 'driver', 'total_kasa',
                    'efficiency', 'average_price', 'mileage',
                    'total_orders', 'total_orders_rejected', 'total_orders_accepted', 'accept_percent', 'road_time']
        else:
            return ['report_from', 'driver', 'total_kasa',
                    'efficiency', 'average_price', 'mileage',
                    'total_orders', 'accept_percent', 'road_time']

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            ('Водій', {'fields': ['report_from', 'driver',
                                  ]}),
            ('Інформація по водію', {'fields': ['total_kasa', 'average_price', 'efficiency',
                                                'mileage']}),
            ('Додатково', {'fields': ['total_orders', 'accept_percent', 'road_time'
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

    def get_list_filter(self, request):
        list_filter = [RentInformationUserFilter, 'created_at']
        if request.user.is_superuser:
            list_filter.insert(0, 'partner')
        return list_filter

    def get_list_display(self, request):
        if request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        else:
            return ['report_from', 'driver', 'rent_distance',
                    ]

    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
            fieldsets = [
                ('Водій', {'fields': ['driver',
                                      ]}),
                ('Інформація про оренду', {'fields': ['report_from', 'rent_distance',
                                                      ]}),
                ('Додатково', {'fields': ['partner',
                                          ]}),
            ]

        else:
            fieldsets = [
                ('Водій', {'fields': ['driver',
                                      ]}),
                ('Інформація про оренду', {'fields': ['report_from', 'rent_distance',
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


class BaseReportAdmin(admin.ModelAdmin):
    list_per_page = 25
    raw_id_fields = ['vehicle', 'partner']
    list_select_related = ['vehicle', 'partner']

    def get_list_display(self, request):
        display = ['report_from', 'report_to', 'driver',
                   'total_amount_without_fee', 'total_amount_cash', 'total_amount_on_card',
                   'total_distance', 'total_rides']
        if request.user.is_superuser:
            display.append('partner')
        return display

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            ('Інформація про звіт', {'fields': ['report_from', 'report_to']}),
            ('Інформація про водія', {'fields': ['driver']}),
            ('Інформація про кошти', {'fields': ['total_amount_cash', 'total_amount_on_card', 'total_amount',
                                                 'tips', 'bonuses', 'fares', 'fee', 'total_amount_without_fee']}),
            ('Інформація про поїздки', {'fields': ['total_rides', 'total_distance']})
        ]
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


@admin.register(Payments)
@admin.register(WeeklyReport)
@admin.register(DailyReport)
@admin.register(CustomReport)
class PaymentsOrderAdmin(BaseReportAdmin):
    search_fields = ('fleet',)

    def get_list_filter(self, request):
        list_filter = [ReportUserFilter]
        if request.user.is_superuser:
            list_filter.insert(0, 'partner')
        return list_filter

    def get_list_display(self, request):
        base_list_display = super().get_list_display(request)
        return base_list_display + ['fleet']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_partner():
            qs = qs.filter(partner=request.user)
        elif request.user.is_manager():
            manager_drivers = Driver.objects.filter(manager=request.user)
            qs = qs.filter(driver__in=manager_drivers)
        return qs.select_related('partner').prefetch_related(
            Prefetch('fleet', queryset=Fleet.objects.only('name')),
            Prefetch('driver', queryset=Driver.objects.only('name', 'second_name')),
        )


@admin.register(SummaryReport)
class SummaryReportAdmin(BaseReportAdmin):
    list_filter = (SummaryReportUserFilter,)

    def get_list_filter(self, request):
        list_filter = [SummaryReportUserFilter]
        if request.user.is_superuser:
            list_filter.insert(0, 'partner')
        return list_filter

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related('partner', 'driver')
        if request.user.is_partner():
            return qs.filter(partner=request.user)
        elif request.user.is_manager():
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


class InvestorForm(forms.ModelForm):
    vehicles = forms.ModelMultipleChoiceField(
        queryset=Vehicle.objects.none(),
        required=False,
        widget=FilteredSelectMultiple('Автомобілі', False)
    )

    class Meta:
        model = Investor
        fields = ('email', 'last_name', 'first_name', 'vehicles')


class InvestorAddForm(forms.ModelForm):
    class Meta:
        model = Investor
        fields = ('email', 'last_name', 'first_name', 'password', 'investors_partner')


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
                email=obj.email
            )
            user.groups.add(Group.objects.get(name='Investor'))
            if request.user.is_partner():
                user.investors_partner_id = request.user.pk
            else:
                user.investors_partner = obj.investors_partner
            user.save()
        else:
            super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, change=False, **kwargs):
        if obj is None:
            form = InvestorAddForm
            if 'investors_partner' in form.base_fields and request.user.is_partner():
                del form.base_fields['investors_partner']
        else:
            form = InvestorForm
            form.base_fields['vehicles'].queryset = Vehicle.objects.filter(
                Q(investor_car__isnull=True) | Q(investor_car=obj), partner=request.user)
            form.base_fields['vehicles'].initial = Vehicle.objects.filter(partner=request.user, investor_car=obj)
        return form

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_partner():
            return qs.filter(investors_partner=request.user)
        return qs

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        if change:
            if 'vehicles' in form.cleaned_data:
                form.instance.vehicle_set.set(form.cleaned_data['vehicles'])


class ManagerForm(forms.ModelForm):
    drivers = forms.ModelMultipleChoiceField(
        queryset=Driver.objects.none(),
        required=False,
        widget=FilteredSelectMultiple('Водії', False)
    )
    vehicles = forms.ModelMultipleChoiceField(
        queryset=Vehicle.objects.none(),
        required=False,
        widget=FilteredSelectMultiple('Автомобілі', False)
    )

    class Meta:
        model = Manager
        fields = ('email', 'last_name', 'first_name', 'chat_id', 'drivers', 'vehicles')


class ManagerAddForm(forms.ModelForm):
    class Meta:
        model = Manager
        fields = ('email', 'last_name', 'first_name', 'chat_id', 'password', 'managers_partner')


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
                chat_id=obj.chat_id,
                email=obj.email
            )
            user.groups.add(Group.objects.get(name='Manager'))
            if request.user.is_partner():
                user.managers_partner_id = request.user.pk
            else:
                user.managers_partner = obj.managers_partner
            user.save()
        else:
            super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_partner():
            return qs.filter(managers_partner=request.user)
        return qs

    def get_form(self, request, obj=None, **kwargs):
        if obj is None:
            form = ManagerAddForm
            if 'managers_partner' in form.base_fields and request.user.is_partner():
                del form.base_fields['managers_partner']
        else:
            form = ManagerForm
            form.base_fields['drivers'].queryset = Driver.objects.filter(Q(manager__isnull=True) | Q(manager=obj),
                                                                         partner=request.user, deleted_at__isnull=True)
            form.base_fields['drivers'].initial = Driver.objects.get_active(partner=request.user, manager=obj)
            form.base_fields['vehicles'].queryset = Vehicle.objects.filter(Q(manager__isnull=True) | Q(manager=obj),
                                                                           partner=request.user,
                                                                           deleted_at__isnull=True)
            form.base_fields['vehicles'].initial = Vehicle.objects.filter(partner=request.user, manager=obj)
        return form

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        if change:
            if 'drivers' in form.cleaned_data:
                form.instance.driver_set.set(form.cleaned_data['drivers'])
            if 'vehicles' in form.cleaned_data:
                form.instance.vehicle_set.set(form.cleaned_data['vehicles'])


@admin.register(Driver)
class DriverAdmin(SoftDeleteAdmin):
    search_fields = ('name', 'second_name')
    ordering = ('second_name', 'name')
    list_display_links = ('name', 'second_name')
    list_per_page = 20
    readonly_fields = ('name', 'second_name', 'email', 'phone_number', 'driver_status')

    def get_list_editable(self, request):
        return ('cash_control',)

    def get_list_filter(self, request):
        list_filter = []
        if request.user.is_superuser:
            list_filter.append('partner')
        return list_filter

    def changelist_view(self, request, extra_context=None):
        self.list_editable = self.get_list_editable(request)
        return super().changelist_view(request, extra_context)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_partner():
            qs = qs.filter(partner=request.user)
        elif request.user.is_manager():
            qs = qs.filter(manager=request.user)
        return qs.select_related('schema', 'partner', 'manager')

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields if not request.user.is_superuser else tuple()

    def get_list_display(self, request):
        if request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        elif request.user.is_partner():
            return ['name', 'second_name',
                    'manager', 'chat_id',
                    'driver_status', 'schema', 'cash_control',
                    'created_at',
                    ]
        else:
            return ['name', 'second_name',
                    'chat_id', 'schema',
                    'driver_status', 'cash_control'
                    ]

    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
            fieldsets = (
                ('Інформація про водія', {'fields': ['name', 'second_name', 'email',
                                                     'phone_number', 'chat_id',
                                                     ]}),
                ('Тарифний план', {'fields': ('schema',
                                              )}),
                ('Додатково', {'fields': ['cash_control', 'partner', 'manager', 'driver_status'
                                          ]}),
            )

        elif request.user.is_partner():
            fieldsets = (
                ('Інформація про водія', {'fields': ['name', 'second_name', 'email',
                                                     'phone_number', 'chat_id',
                                                     ]}),
                ('Тарифний план', {'fields': ('schema',
                                              )}),
                ('Додатково', {'fields': ['cash_control', 'driver_status', 'manager',
                                          ]}),
            )
        else:
            fieldsets = (
                ('Інформація про водія', {'fields': ['name', 'second_name', 'email',
                                                     'phone_number', 'chat_id',
                                                     ]}),
                ('Тарифний план', {'fields': ('schema',
                                              )}),
                ('Додатково', {'fields': ['cash_control', 'driver_status',
                                          ]}),
            )
        return fieldsets

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if request.user.is_partner():
            if db_field.name == 'schema':
                kwargs['queryset'] = db_field.related_model.objects.filter(partner=request.user).only('title')
            if db_field.name == 'manager':
                kwargs['queryset'] = db_field.related_model.objects.filter(
                    managers_partner=request.user).only('first_name', 'last_name')
        elif request.user.is_manager():
            if db_field.name == 'schema':
                manager = Manager.objects.get(pk=request.user.pk)
                kwargs['queryset'] = db_field.related_model.objects.filter(
                    partner=manager.managers_partner).only('title')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        fleet = NinjaFleet.objects.filter(partner=obj.partner)
        if fleet:
            chat_id = form.cleaned_data.get('chat_id')
            if chat_id:
                FleetsDriversVehiclesRate.objects.get_or_create(fleet=fleet.first(),
                                                                driver_external_id=chat_id,
                                                                defaults={
                                                                    'driver': obj,
                                                                    'partner': obj.partner}
                                                                )

        super().save_model(request, obj, form, change)


@admin.register(DeletedVehicle)
class DeletedVehicleAdmin(admin.ModelAdmin):
    list_display = ('licence_plate', 'name', 'deleted_at')
    list_filter = ('deleted_at',)
    search_fields = ('licence_plate', 'name')
    list_per_page = 25

    def get_queryset(self, request):
        qs = super().get_queryset(request).filter(deleted_at__isnull=False)
        if request.user.is_partner():
            return qs.filter(partner_id=request.user.pk)
        return qs

    change_form_template = 'admin/change_form_fired_driver.html'

    def get_fieldsets(self, request, obj=None):
        fieldsets = (
            ('Інформація про авто', {'fields': ['name', 'licence_plate',
                                                ]}),
        )
        return fieldsets

    def get_list_filter(self, request):
        list_filter = []
        if request.user.is_superuser:
            list_filter.append('partner')
        return list_filter

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
                list_url = reverse('admin:app_deletedvehicle_changelist')
                return HttpResponseRedirect(list_url)

        return super().change_view(request, object_id, form_url, extra_context)


@admin.register(FiredDriver)
class FiredDriverAdmin(admin.ModelAdmin):
    readonly_fields = ('name', 'second_name')
    search_fields = ('name', 'second_name')

    def get_list_filter(self, request):
        list_filter = []
        if request.user.is_superuser:
            list_filter.append('partner')
        return list_filter

    def get_list_display(self, request):
        if request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        elif request.user.is_partner():
            return ['name', 'second_name',
                    'manager', 'chat_id',
                    'schema',
                    ]
        else:
            return ['name', 'second_name',
                    'chat_id', 'schema',
                    ]

    def get_model_perms(self, request):
        perms = super().get_model_perms(request)
        if request.user.is_partner():
            perms.update(view=True, change=False, add=False, delete=False)
        return perms

    def get_fieldsets(self, request, obj=None):
        fieldsets = (
            ('Інформація про водія', {'fields': ['name', 'second_name',
                                                 ]}),
        )
        return fieldsets

    def get_queryset(self, request):
        qs = super().get_queryset(request).filter(deleted_at__isnull=False)
        if request.user.is_partner():
            return qs.filter(partner_id=request.user.pk).select_related('schema')
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
class VehicleAdmin(SoftDeleteAdmin):
    search_fields = ('name', 'licence_plate', 'vin_code',)
    ordering = ('licence_plate',)
    exclude = ('deleted_at',)
    list_display_links = ('licence_plate',)
    list_per_page = 10
    readonly_fields = ('licence_plate', 'name')

    def get_list_filter(self, request):
        list_filter = [VehicleManagerFilter]
        if request.user.is_superuser:
            list_filter.insert(0, 'partner')
        return list_filter

    def get_list_display(self, request):
        if request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        elif request.user.is_partner():
            return ['licence_plate', 'name',
                    'vin_code', 'gps',
                    'purchase_price',
                    'manager', 'investor_car', 'investor_schema', 'branding', 'created_at'
                    ]
        else:
            return ['licence_plate', 'name',
                    'vin_code', 'gps',
                    'purchase_price'
                    ]

    def get_list_editable(self, request):
        if request.user.is_partner():
            return ('purchase_price',)
        else:
            return []

    def changelist_view(self, request, extra_context=None):
        self.list_editable = self.get_list_editable(request)
        return super().changelist_view(request, extra_context)

    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
            fieldsets = [
                ('Номер автомобіля', {'fields': ['licence_plate',
                                                 ]}),
                ('Інформація про машину', {'fields': ['name', 'purchase_price',
                                                      'currency', 'investor_car', 'investor_schema',
                                                      'investor_percentage', 'rental_price',
                                                      'currency_rate', 'currency_back',
                                                      ]}),
                ('Особисті дані авто', {'fields': ['vin_code', 'gps_imei', 'lat', 'lon',
                                                   'car_status', 'gps',
                                                   ]}),
                ('Додатково', {'fields': ['chat_id', 'partner', 'manager', 'branding'
                                          ]}),
            ]

        elif request.user.is_partner():
            fieldsets = (
                ('Інформація про машину', {'fields': ['licence_plate', 'name', 'purchase_price', 'purchase_date'
                                                      ]}),
                ('Дані авто з GPS', {'fields': ['gps_imei', 'gps', 'start_mileage'
                                                ]}),
                ('Інформація про інвестора', {'fields': ['currency', 'investor_car', 'investor_schema',
                                                         'rental_price',
                                                         'investor_percentage', 'currency_rate', 'currency_back',
                                                         ]}),
                ('Додатково', {'fields': ['manager', 'branding'
                                          ]}),
            )
        elif request.user.is_manager():
            fieldsets = (
                ('Номер автомобіля', {'fields': ['licence_plate',
                                                 ]}),
                ('Інформація про машину', {'fields': ['name', 'gps_imei', 'gps', 'purchase_date', 'start_mileage'
                                                      ]}),
            )
        else:
            fieldsets = (
                ('Номер автомобіля', {'fields': ['licence_plate', 'gps_imei',
                                                 ]}),
                ('Інформація про машину', {'fields': ['name', 'purchase_price',
                                                      ]}),
            )
        return fieldsets

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        filter_mapping = {
            'investor_car': ('investors_partner', ('first_name', 'last_name')),
            'manager': ('managers_partner', ('first_name', 'last_name')),
            'gps': ('partner', ('name',)),
            'branding': ('partner', ('name',))
        }
        if request.user.is_partner():
            related_field_name = filter_mapping.get(db_field.name)
            if related_field_name:
                filter_param = {related_field_name[0]: request.user}
                kwargs['queryset'] = db_field.related_model.objects.filter(
                    **filter_param).only(*related_field_name[1])
        elif request.user.is_manager():
            if db_field.name == 'gps':
                manager = Manager.objects.get(pk=request.user.pk)
                kwargs['queryset'] = db_field.related_model.objects.filter(partner=manager.managers_partner.pk).only(
                    'name')

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_manager():
            return qs.filter(manager=request.user)
        if request.user.is_partner():
            return qs.filter(partner=request.user)
        if request.user.is_investor():
            return qs.filter(investor_car=request.user)
        return qs.select_related('gps', 'manager', 'partner','investor_car')


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
                ('Адреси', {'fields': ['from_address', 'to_the_address',
                                       ]}),
                ('Контакти', {'fields': ['phone_number', 'chat_id_client',
                                         ]}),
                ('Ціни', {'fields': ['car_delivery_price', 'sum',
                                     ]}),
                ('Деталі', {'fields': ['payment_method', 'order_time',
                                       'status_order', 'distance_gps',
                                       'distance_google', 'driver',
                                       ]}),
            ]
        else:
            fieldsets = [
                ('Адреси', {'fields': ['from_address', 'to_the_address',
                                       ]}),
                ('Контакти', {'fields': ['phone_number',
                                         ]}),
                ('Ціни', {'fields': ['car_delivery_price', 'sum',
                                     ]}),
                ('Деталі', {'fields': ['payment_method', 'order_time',
                                       'status_order', 'distance_gps',
                                       'distance_google', 'driver',
                                       ]}),
            ]

        return fieldsets


@admin.register(FleetOrder)
class FleetOrderAdmin(admin.ModelAdmin):

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('vehicle', 'partner', 'driver')

    def get_list_filter(self, request):
        list_filter = ['fleet', FleetOrderFilter, 'partner']
        return list_filter

    def get_list_display(self, request):
        return ('order_id', 'fleet', 'driver', 'from_address', 'destination',
                'accepted_time', 'finish_time',
                'state', 'payment', 'price', 'vehicle_id', 'date_order'
                )

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            ('Адреси', {'fields': ['from_address', 'destination', ]}),
            ('Інформація', {'fields': ['driver', 'fleet', 'state']}),
            ('Час', {'fields': ['accepted_time', 'finish_time', 'date_order']}),
            ('Ціна', {'fields': ['price', 'payment', 'tips', ]}),
        ]

        return fieldsets


@admin.register(FleetsDriversVehiclesRate)
class FleetsDriversVehiclesRateAdmin(admin.ModelAdmin):
    list_per_page = 25
    list_filter = ['partner', 'driver']

    def get_list_display(self, request):
        return ('fleet', 'driver', 'pay_cash',
                'driver_external_id',
                )

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            ('Деталі', {'fields': ['fleet', 'driver',
                                   'driver_external_id',
                                   ]}),
        ]
        if request.user.is_superuser:
            fieldsets.append(('Додатково', {'fields': ['partner', 'deleted_at',
                                   'pay_cash',
                                   ]}))

        return fieldsets



    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if request.user.is_partner():
            filter_map = {"driver": Q(partner=request.user, deleted_at__isnull=True),
                                  "fleet": Q(partner=request.user)}
        elif request.user.is_manager():
            filter_map = {"driver": Q(manager=request.user, deleted_at__isnull=True),
                                      "fleet": Q(partner__manager=request.user)}
        else:
            filter_map = {
                      "driver": Q(deleted_at__isnull=True), "fleet": Q()
                      }

        if db_field.name == "driver":
            kwargs["queryset"] = Driver.objects.filter(filter_map[db_field.name]).select_related('partner')
        if db_field.name == "fleet":
            kwargs["queryset"] = Fleet.objects.filter(filter_map[db_field.name]).select_related('partner')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_partner():
            qs = qs.filter(partner=request.user)
        elif request.user.is_manager():
            manager = Manager.objects.get(pk=request.user.pk)
            qs = qs.filter(partner=manager.managers_partner)
        return qs.select_related('fleet__partner', 'driver__partner').prefetch_related(
            Prefetch('fleet', queryset=Fleet.objects.only('name')),
            Prefetch('driver', queryset=Driver.objects.only('name', 'second_name')),
        )


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
                ('Деталі', {'fields': ['comment', 'chat_id',
                                       'processed', 'partner',
                                       ]}),
            ]
        else:
            fieldsets = [
                ('Деталі', {'fields': ['comment', 'chat_id',
                                       'processed', 'partner',
                                       ]}),

            ]

        return fieldsets


# class ParkSettingsForm(forms.ModelForm):
#     class Meta:
#         model = ParkSettings
#         fields = ('value', 'description')
#
#     def clean_value(self):
#         value = self.cleaned_data.get('value')
#
#         try:
#             int_value = int(value)
#         except (ValueError, TypeError):
#             raise forms.ValidationError("Введіть, будь ласка, ціле число")
#
#         return int_value


@admin.register(ParkSettings)
class ParkSettingsAdmin(admin.ModelAdmin):
    # form = ParkSettingsForm

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            qs = qs.filter(partner=request.user)
        return qs

    def get_list_display(self, request):
        if request.user.is_partner():
            return ['description', 'value']
        return [f.name for f in self.model._meta.fields]


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


@admin.register(DriverReshuffle)
class DriverReshuffle(admin.ModelAdmin):
    list_display = ['driver_start', 'swap_vehicle', 'swap_time', 'end_time']
    list_filter = ['partner', 'driver_start', 'swap_vehicle']
    fieldsets = [
        ('Інформація', {'fields': ['driver_start', 'swap_vehicle', 'swap_time', 'end_time'
                                   ]}),
    ]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_partner():
            qs.filter(driver_start__partner=request.user)
        elif request.user.is_manager():
            drivers = Driver.objects.filter(manager=request.user)
            qs.filter(driver_start__in=drivers)
        return qs.select_related('driver_start', 'swap_vehicle')


@admin.register(DriverPayments)
class DriverPaymentsAdmin(admin.ModelAdmin):
    list_display = ['report_from', 'report_to', 'driver', 'status', 'earning']
    list_filter = ['partner', 'driver']


@admin.register(DriverEfficiencyFleet)
class DriverFleetEfficiencyAdmin(admin.ModelAdmin):
    list_display = ['report_from', 'driver', 'efficiency', 'total_kasa', 'total_orders_accepted', 'mileage', 'fleet']

    def get_list_filter(self, request):
        if request.user.is_superuser:
            return ['partner', 'driver']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_partner():
            qs = qs.filter(partner=request.user)
        if request.user.is_manager():
            qs = qs.filter(driver__manager=request.user)
        return qs.select_related('fleet__partner', 'driver__partner').prefetch_related(
            Prefetch('fleet', queryset=Fleet.objects.only('name')),
            Prefetch('driver', queryset=Driver.objects.only('name', 'second_name')),
        )


@admin.register(SpendingCategory)
class SpendingCategory(admin.ModelAdmin):
    list_display = ['title']

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            ('Назва категорії', {'fields': ['title',
                                   ]}),

        ]

        return fieldsets

    def save_model(self, request, obj, form, change):
        if request.user.is_partner():
            obj.partner_id = request.user.pk
        if request.user.is_manager():
            obj.partner = request.user.manager.managers_partner
        super().save_model(request, obj, form, change)


@admin.register(SubscribeUsers)
class SubscribeUsersAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone_number', 'email', 'created_at']
    list_filter = ['created_at']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_partner():
            qs = qs.filter(partner=request.user)
        return qs
