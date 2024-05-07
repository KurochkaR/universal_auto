from rest_framework import serializers

from app.models import DriverPayments, Bonus, Penalty, Driver, DriverEfficiencyPolymorphic, Vehicle, DriverEfficiency


class AggregateReportSerializer(serializers.Serializer):
    full_name = serializers.CharField()
    total_kasa = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_card = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_cash = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    weekly_payments = serializers.DecimalField(max_digits=10, decimal_places=2)


class CarDetailSerializer(serializers.Serializer):
    start_date = serializers.CharField()
    end_date = serializers.CharField()
    licence_plate = serializers.CharField()
    price = serializers.IntegerField()
    kasa = serializers.DecimalField(max_digits=10, decimal_places=2)
    spending = serializers.DecimalField(max_digits=10, decimal_places=2)
    progress_percentage = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_progress_percentage = serializers.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        fields = (
            "licence_plate", "price", "kasa", "spending", "progress_percentage", "total_progress_percentage",
            "start_date", "end_date"
        )


class FleetEfficiencySerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverEfficiencyPolymorphic
        fields = (
            "total_kasa",
            "total_orders",
            "total_orders_rejected",
            "total_orders_accepted",
            "accept_percent",
            "average_price",
            "road_time",
            "efficiency",
            "mileage",
        )


class DriverEfficiencyFleetSerializer(serializers.Serializer):
    full_name = serializers.CharField()
    fleets = serializers.ListField(child=serializers.DictField(child=FleetEfficiencySerializer()))


class DriverEfficiencyFleetRentSerializer(serializers.Serializer):
    start = serializers.CharField()
    end = serializers.CharField()
    drivers_efficiency = serializers.ListField(child=DriverEfficiencyFleetSerializer())


class DriverEfficiencySerializer(FleetEfficiencySerializer):
    full_name = serializers.CharField()

    class Meta:
        model = DriverEfficiency
        fields = (
            "full_name",
            "total_kasa",
            "total_orders",
            "total_orders_accepted",
            "total_orders_rejected",
            "average_price",
            "road_time",
            "efficiency",
            "mileage",
            "rent_distance"
        )


class DriverEfficiencyRentSerializer(serializers.Serializer):
    start = serializers.CharField()
    end = serializers.CharField()
    drivers_efficiency = DriverEfficiencySerializer(many=True)


class VehiclesEfficiencySerializer(serializers.Serializer):
    efficiency = serializers.ListField(child=serializers.FloatField())
    mileage = serializers.ListField(child=serializers.FloatField())


class CarEfficiencySerializer(serializers.Serializer):
    dates = serializers.ListField(child=serializers.DateTimeField())
    vehicles = VehiclesEfficiencySerializer(many=True)
    total_mileage = serializers.DecimalField(max_digits=10, decimal_places=2)
    average_efficiency = serializers.DecimalField(max_digits=10, decimal_places=2)
    earning = serializers.DecimalField(max_digits=10, decimal_places=2)
    vehicle_list = serializers.ListField(child=serializers.CharField())
    # mileage = serializers.ListField(child=serializers.DecimalField(max_digits=10, decimal_places=2))
    efficiency = serializers.ListField(child=serializers.DecimalField(max_digits=10, decimal_places=2))


class SummaryReportSerializer(serializers.Serializer):
    drivers = AggregateReportSerializer(many=True)
    rent_earnings = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_distance = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_rent = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_payment = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    kasa = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_vehicle_spending = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_driver_spending = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    start = serializers.CharField()
    end = serializers.CharField()


class CarEarningsSerializer(serializers.Serializer):
    licence_plate = serializers.CharField()
    earnings = serializers.DecimalField(max_digits=10, decimal_places=2)
    mileage = serializers.DecimalField(max_digits=10, decimal_places=2)


class TotalEarningsSerializer(serializers.Serializer):
    total_earnings = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_mileage = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_spending = serializers.DecimalField(max_digits=10, decimal_places=2)
    roi = serializers.IntegerField()


class InvestorCarsSerializer(serializers.Serializer):
    car_earnings = CarEarningsSerializer(many=True)
    totals = TotalEarningsSerializer()
    start = serializers.CharField()
    end = serializers.CharField()


class DriverChangesSerializer(serializers.Serializer):
    date = serializers.DateField()
    driver_name = serializers.CharField()
    driver_id = serializers.IntegerField()
    vehicle_id = serializers.IntegerField()
    driver_photo = serializers.CharField()
    start_shift = serializers.TimeField()
    end_shift = serializers.TimeField()
    reshuffle_id = serializers.IntegerField()
    dtp_maintenance = serializers.CharField()


class ReshuffleSerializer(serializers.Serializer):
    swap_licence = serializers.CharField()
    vehicle_brand = serializers.CharField()
    reshuffles = DriverChangesSerializer(many=True)


class BonusSerializer(serializers.ModelSerializer):
    vehicle = serializers.CharField(source='vehicle.licence_plate')
    category = serializers.CharField(source='category.title')

    class Meta:
        model = Bonus
        fields = ('id', 'amount', 'category', 'vehicle', 'driver')


class PenaltySerializer(serializers.ModelSerializer):
    vehicle = serializers.CharField(source='vehicle.licence_plate')
    category = serializers.CharField(source='category.title')

    class Meta:
        model = Penalty
        fields = ('id', 'amount', 'category', 'vehicle', 'driver')


class DriverPaymentsSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField()
    driver_vehicles = serializers.ListField(child=serializers.IntegerField())
    status = serializers.SerializerMethodField()
    report_from = serializers.DateTimeField(format='%d.%m.%Y %H:%M')
    report_to = serializers.DateTimeField(format='%d.%m.%Y %H:%M')
    rate = serializers.IntegerField()
    bonuses = serializers.DecimalField(max_digits=10, decimal_places=2)
    penalties = serializers.DecimalField(max_digits=10, decimal_places=2)
    bonuses_list = serializers.SerializerMethodField()
    penalties_list = serializers.SerializerMethodField()

    def get_bonuses_list(self, obj):
        bonuses = [pb for pb in obj.prefetched_penaltybonuses if isinstance(pb, Bonus)]
        return BonusSerializer(bonuses, many=True).data

    def get_penalties_list(self, obj):
        penalties = [pb for pb in obj.prefetched_penaltybonuses if isinstance(pb, Penalty)]
        return PenaltySerializer(penalties, many=True).data

    def get_status(self, obj):
        return obj.get_status_display()

    class Meta:
        model = DriverPayments
        fields = ('full_name', 'driver_vehicles', 'kasa', 'cash', 'rent', 'rate', 'earning', 'salary',
                  'status', 'bolt_screen', 'report_from', 'report_to', 'id', 'bonuses', 'penalties',
                  'payment_type', 'bonuses_list', 'penalties_list')


class DriverInformationSerializer(serializers.ModelSerializer):
    photo = serializers.CharField()
    full_name = serializers.CharField()
    vehicle = serializers.CharField()
    driver_schema = serializers.CharField()

    class Meta:
        model = Driver
        fields = (
            "id", "photo", "full_name", "phone_number", "chat_id", "driver_schema", "driver_status", "vehicle"
        )
