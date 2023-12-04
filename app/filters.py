from django.contrib import admin

from app.models import CarEfficiency, Vehicle, DriverEfficiency, Driver, RentInformation, \
    TransactionsConversation, SummaryReport, Payments, FleetOrder, Fleets_drivers_vehicles_rate, Manager, Partner, \
    Investor


class VehicleEfficiencyUserFilter(admin.SimpleListFilter):
    title = 'номером автомобіля'
    parameter_name = 'efficiency_vehicle_partner_user'

    def lookups(self, request, model_admin):
        user = request.user
        queryset = CarEfficiency.objects.all()
        vehicle_choices = []
        if user.is_manager():
            vehicles = Vehicle.objects.filter(manager=user)
            queryset = queryset.filter(vehicle__in=vehicles)
        elif user.is_partner():
            queryset = queryset.filter(partner=user)
        elif user.is_investor():
            vehicles = Vehicle.objects.filter(investor_car=user)
            queryset = queryset.filter(vehicle__in=vehicles)
        vehicle_choices.extend(queryset.values_list('vehicle_id', 'vehicle__licence_plate'))
        return sorted(set(vehicle_choices), key=lambda x: x[1])

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(vehicle__id=int(value))


class TransactionInvestorUserFilter(admin.SimpleListFilter):
    title = 'номером автомобіля'
    parameter_name = 'transaction_investor_user'

    def lookups(self, request, model_admin):
        user = request.user
        queryset = TransactionsConversation.objects.all()
        vehicle_choices = []
        if user.is_investor():
            vehicles = Vehicle.objects.filter(investor_car=user)
            queryset.filter(vehicle__in=vehicles)
        if user.is_partner():
            queryset = TransactionsConversation.objects.filter(investor__investors_partner=user)
        vehicle_choices.extend(queryset.values_list('vehicle_id', 'vehicle__licence_plate'))
        return sorted(set(vehicle_choices), key=lambda x: x[1])

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(vehicle__id=int(value))


class ChildModelFilter(admin.SimpleListFilter):
    title = 'Child Service'
    parameter_name = 'child_service'

    def lookups(self, request, model_admin):
        child_models = model_admin.child_models
        return [(str(model.id), model.__name__) for model in child_models]

    def queryset(self, request, queryset):
        child_model_id = self.value()
        if child_model_id:
            return queryset.filter(polymorphic_ctype_id=child_model_id)
        return queryset


class VehicleManagerFilter(admin.SimpleListFilter):
    parameter_name = 'vehicle_manager_user'
    title = 'менеджером'

    def lookups(self, request, model_admin):
        user = request.user
        queryset = Vehicle.objects.exclude(manager__isnull=True).select_related('manager', 'gps')
        if user.is_partner():
            queryset = queryset.filter(partner=user)
            manager_ids = queryset.values_list('manager_id', flat=True)
            manager_labels = [f'{item.manager.first_name} {item.manager.last_name}' for item in queryset]
            return set(zip(manager_ids, manager_labels))

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            if request.user.is_partner():
                return queryset.filter(manager__id=value)


class DriverRelatedFilter(admin.SimpleListFilter):
    parameter_name = None
    model_class = None
    title = 'водієм'

    def lookups(self, request, model_admin):
        user = request.user
        queryset = self.model_class.objects.exclude(driver__isnull=True).select_related("driver")
        if user.is_manager():
            drivers = Driver.objects.filter(manager=user)
            queryset = queryset.filter(driver__in=drivers)
        if user.is_partner():
            queryset = queryset.filter(partner=user)
        driver_ids = queryset.values_list('driver_id', flat=True)
        driver_labels = [f'{item.driver.name} {item.driver.second_name}' for item in queryset]
        return set(zip(driver_ids, driver_labels))

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(driver__id=value)


class DriverEfficiencyUserFilter(DriverRelatedFilter):
    parameter_name = 'driver_efficiency_user'
    model_class = DriverEfficiency


class SummaryReportUserFilter(DriverRelatedFilter):
    parameter_name = 'summary_report_user'
    model_class = SummaryReport


class RentInformationUserFilter(DriverRelatedFilter):
    parameter_name = 'rent_information_user'
    model_class = RentInformation


class FleetOrderFilter(DriverRelatedFilter):
    parameter_name = 'fleet_order_user'
    model_class = FleetOrder


class PaymentsRelatedFilter(admin.SimpleListFilter):
    parameter_name = None
    model_class = None
    title = 'водієм'

    def lookups(self, request, model_admin):
        user = request.user
        queryset = self.model_class.objects.all()
        if user.is_manager():
            drivers = Driver.objects.filter(manager=user)
            full_names = [f"{driver.name} {driver.second_name}" for driver in drivers]
            queryset = queryset.filter(full_name__in=full_names)
        if user.is_partner():
            queryset = queryset.filter(partner=user)

        driver_labels = set([driver.full_name for driver in queryset])
        return [(full_name, full_name) for full_name in driver_labels]

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(full_name=value)


class ReportUserFilter(PaymentsRelatedFilter):
    parameter_name = 'payment_report_user'
    model_class = Payments


class FleetRelatedFilter(admin.SimpleListFilter):
    parameter_name = "fleet_driver_user"
    title = 'автопарком'

    def lookups(self, request, model_admin):
        user = request.user
        queryset = Fleets_drivers_vehicles_rate.objects.all()
        fleet_choices = []
        if user.is_partner():
            queryset = queryset.filter(partner=user)
        if user.is_manager():
            queryset = queryset.filter(partner=request.user.managers_partner)
        fleet_choices.extend(queryset.values_list('fleet_id', 'fleet__name'))
        return set(fleet_choices)

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(fleet__id=value)
