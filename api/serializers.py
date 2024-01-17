from django.db.models import Sum
from rest_framework import serializers

from app.models import DriverPayments, Bonus, Penalty, DriverEfficiencyFleet


class AggregateReportSerializer(serializers.Serializer):
    full_name = serializers.CharField()
    total_kasa = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_card = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_cash = serializers.DecimalField(max_digits=10, decimal_places=2)


class CarDetailSerializer(serializers.Serializer):
    licence_plate = serializers.CharField()
    price = serializers.IntegerField()
    kasa = serializers.DecimalField(max_digits=10, decimal_places=2)
    spending = serializers.DecimalField(max_digits=10, decimal_places=2)
    progress_percentage = serializers.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        fields = ("licence_plate", "price", "kasa", "spending", "progress_percentage")


class DriverEfficiencySerializer(serializers.Serializer):
    full_name = serializers.CharField()
    driver_total_kasa = serializers.DecimalField(max_digits=10, decimal_places=2)
    orders = serializers.IntegerField()
    driver_accept_percent = serializers.IntegerField()
    driver_road_time = serializers.DurationField()
    driver_efficiency = serializers.DecimalField(max_digits=10, decimal_places=2)
    driver_mileage = serializers.DecimalField(max_digits=10, decimal_places=2)
    driver_average_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    rent_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    fleet_name = serializers.SerializerMethodField()

    def get_fleet_name(self, obj):
        return obj.fleet.name if isinstance(obj, DriverEfficiencyFleet) else None

    class Meta:
        fields = (
            "full_name",
            "driver_total_kasa",
            "total_orders",
            "driver_accept_percent",
            "driver_average_price",
            "driver_road_time",
            "driver_efficiency",
            "driver_mileage",
            "rent_amount",
            "fleet_name",
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
    kasa = serializers.DecimalField(max_digits=10, decimal_places=2)
    earning = serializers.DecimalField(max_digits=10, decimal_places=2)


class SummaryReportSerializer(serializers.Serializer):
    drivers = AggregateReportSerializer(many=True)
    total_rent = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
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
        fields = ('full_name', 'kasa', 'cash', 'rent', 'earning', 'status', 'report_from',
                  'report_to', 'id', 'bonuses', 'penalties', 'bonuses_list', 'penalties_list')
