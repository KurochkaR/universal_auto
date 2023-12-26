from django.db.models import Sum
from rest_framework import serializers

from app.models import DriverPayments, Bonus, Penalty


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
    total_kasa = serializers.DecimalField(max_digits=10, decimal_places=2)
    orders = serializers.IntegerField()
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


class VehiclesEfficiencySerializer(serializers.Serializer):
    efficiency = serializers.ListField(child=serializers.FloatField())
    mileage = serializers.ListField(child=serializers.FloatField())


class CarEfficiencySerializer(serializers.Serializer):
    dates = serializers.ListField(child=serializers.DateField())
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


class DriverPaymentsSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    report_from = serializers.DateField(format='%d.%m.%Y')
    report_to = serializers.DateField(format='%d.%m.%Y')
    bonuses = serializers.SerializerMethodField()
    penalties = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        return f"{obj.driver.user_ptr.name} {obj.driver.user_ptr.second_name}"

    def get_status(self, obj):
        return obj.get_status_display()

    def get_bonuses(self, obj):
        return obj.bonus_set.all().aggregate(Sum('amount'))['amount__sum'] or 0

    def get_penalties(self, obj):
        return obj.penalty_set.all().aggregate(Sum('amount'))['amount__sum'] or 0

    class Meta:
        model = DriverPayments
        fields = ('full_name', 'kasa', 'cash', 'rent', 'earning', 'status', 'report_from',
                  'report_to', 'id', 'bonuses', 'penalties')
