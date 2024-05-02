from django.contrib import admin

from app.models import CarEfficiency, Vehicle, DriverEfficiency, Driver, RentInformation, \
    InvestorPayments, SummaryReport, Payments, FleetOrder, FleetsDriversVehiclesRate, PartnerEarnings, Manager, \
    VehicleSpending


class VehicleRelatedFilter(admin.SimpleListFilter):
    parameter_name = None
    model_class = None
    title = 'номером автомобіля'

    def lookups(self, request, model_admin):
        user = request.user
        queryset = self.model_class.objects.all()
        vehicle_choices = []
        if user.is_manager():
            queryset = queryset.filter(vehicle__manager=user.pk)
        elif user.is_partner():
            queryset = queryset.filter(partner=user)
        elif user.is_investor():
            queryset = queryset.filter(vehicle__investor_car=user.pk)
        vehicle_choices.extend(queryset.values_list('vehicle_id', 'vehicle__licence_plate'))
        return sorted(set(vehicle_choices), key=lambda x: x[1])

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(vehicle__id=int(value))


class VehicleEfficiencyUserFilter(VehicleRelatedFilter):
    parameter_name = 'efficiency_vehicle_partner_user'
    model_class = CarEfficiency


class VehicleSpendingFilter(VehicleRelatedFilter):
    parameter_name = 'spending_vehicle_user'
    model_class = VehicleSpending


class PartnerPaymentFilter(admin.SimpleListFilter):
    title = 'номером автомобіля'
    parameter_name = 'partner_payments_user'

    def lookups(self, request, model_admin):
        user = request.user
        queryset = PartnerEarnings.objects.all().select_related('vehicle', 'driver')
        vehicle_choices = []
        if user.is_partner():
            queryset.filter(vehicle__partner=user)

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
        queryset = InvestorPayments.objects.all().select_related("vehicle")
        vehicle_choices = []
        if user.is_investor():
            vehicles = Vehicle.objects.filter(investor_car=user)
            queryset.filter(vehicle__in=vehicles)
        if user.is_partner():
            queryset = InvestorPayments.objects.filter(investor__investors_partner=user)
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
            manager_labels = [f'{item.manager.last_name} {item.manager.first_name}' for item in queryset]
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
        drivers_data = queryset.values('driver_id', 'driver__name', 'driver__second_name')

        driver_id_to_name = {item['driver_id']: f"{item['driver__second_name']} {item['driver__name']}" for item in
                             drivers_data}

        driver_ids = list(driver_id_to_name.keys())
        driver_labels = list(driver_id_to_name.values())
        driver_set = set(zip(driver_ids, driver_labels))
        return sorted(list(driver_set), key=lambda x: x[1])

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


class ReportUserFilter(DriverRelatedFilter):
    parameter_name = 'payment_report_user'
    model_class = Payments


class FleetRelatedFilter(admin.SimpleListFilter):
    parameter_name = None
    model_class = None
    title = 'автопарком'

    def lookups(self, request, model_admin):
        user = request.user
        queryset = self.model_class.objects.all().select_related('fleet')
        fleet_choices = []
        if user.is_partner():
            queryset = queryset.filter(partner=user)
        if user.is_manager():
            manager = Manager.objects.get(pk=request.user.pk)
            queryset = queryset.filter(partner=manager.managers_partner)
        fleet_choices.extend(queryset.values_list('fleet_id', 'fleet__name'))
        return set(fleet_choices)

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(fleet__id=value)


class FleetDriverFilter(FleetRelatedFilter):
    parameter_name = 'fleet_driver_fleet'
    model_class = FleetsDriversVehiclesRate


class FleetFilter(FleetRelatedFilter):
    parameter_name = 'fleet_payment_fleet'
    model_class = Payments
