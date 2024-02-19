from rest_framework import serializers

from app.models import DriverPayments, Bonus, Penalty, Driver


class AggregateReportSerializer(serializers.Serializer):
    full_name = serializers.CharField()
    total_kasa = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_card = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_cash = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_amount = serializers.DecimalField(max_digits=10, decimal_places=2)


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


class DriverEfficiencySerializer(serializers.Serializer):
    full_name = serializers.CharField()
    total_kasa = serializers.DecimalField(max_digits=10, decimal_places=2)
    orders = serializers.IntegerField()
    orders_rejected = serializers.IntegerField()
    accept_percent = serializers.IntegerField()
    road_time = serializers.DurationField()
    efficiency = serializers.DecimalField(max_digits=10, decimal_places=2)
    mileage = serializers.DecimalField(max_digits=10, decimal_places=2)
    average_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    rent_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        fields = (
            "full_name",
            "total_kasa",
            "total_orders",
            "total_orders_rejected",
            "accept_percent",
            "average_price",
            "road_time",
            "efficiency",
            "mileage",
            "rent_amount",
        )


class DriverEfficiencyRentSerializer(serializers.Serializer):
    start = serializers.CharField()
    end = serializers.CharField()
    drivers_efficiency = DriverEfficiencySerializer(many=True)


class FleetEfficiencySerializer(serializers.Serializer):
    driver_total_kasa = serializers.DecimalField(max_digits=10, decimal_places=2)
    orders = serializers.IntegerField()
    orders_rejected = serializers.IntegerField()
    driver_average_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    driver_accept_percent = serializers.DecimalField(max_digits=5, decimal_places=2)
    driver_road_time = serializers.DurationField()
    driver_mileage = serializers.DecimalField(max_digits=10, decimal_places=2)
    driver_efficiency = serializers.DecimalField(max_digits=10, decimal_places=2)


class DriverEfficiencyFleetSerializer(serializers.Serializer):
    full_name = serializers.CharField()
    fleets = serializers.ListField(child=serializers.DictField(child=FleetEfficiencySerializer()))


class DriverEfficiencyFleetRentSerializer(serializers.Serializer):
    start = serializers.CharField()
    end = serializers.CharField()
    drivers_efficiency = serializers.ListField(child=DriverEfficiencyFleetSerializer())


class VehiclesEfficiencySerializer(serializers.Serializer):
    efficiency = serializers.ListField(child=serializers.FloatField())
    mileage = serializers.ListField(child=serializers.FloatField())


class CarEfficiencySerializer(serializers.Serializer):
    dates = serializers.ListField(child=serializers.DateTimeField())
    vehicles = VehiclesEfficiencySerializer(many=True)
    total_mileage = serializers.DecimalField(max_digits=10, decimal_places=2)
    average_efficiency = serializers.DecimalField(max_digits=10, decimal_places=2)
    earning = serializers.DecimalField(max_digits=10, decimal_places=2)


class SummaryReportSerializer(serializers.Serializer):
    drivers = AggregateReportSerializer(many=True)
    total_rent = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_payment = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    kasa = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
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


class ReshuffleSerializer(serializers.Serializer):
    swap_licence = serializers.CharField()
    reshuffles = DriverChangesSerializer(many=True)


class BonusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bonus
        fields = ('id', 'amount', 'description', 'driver')


class PenaltySerializer(serializers.ModelSerializer):
    class Meta:
        model = Penalty
        fields = ('id', 'amount', 'description', 'driver')


class DriverPaymentsSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField()
    driver_vehicles = serializers.ListField(child=serializers.IntegerField())
    status = serializers.SerializerMethodField()
    report_from = serializers.DateTimeField(format='%d.%m.%Y %H:%M')
    report_to = serializers.DateTimeField(format='%d.%m.%Y %H:%M')
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
        fields = ('full_name', 'driver_vehicles', 'kasa', 'cash', 'rent', 'earning', 'salary', 'status', 'report_from',
                  'report_to', 'id', 'bonuses', 'penalties', 'bonuses_list', 'penalties_list')


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
