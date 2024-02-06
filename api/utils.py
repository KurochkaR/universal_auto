from datetime import timedelta
from decimal import Decimal

from django.db.models import OuterRef, Sum, DecimalField, F, Value, Avg, CharField, ExpressionWrapper, Case, When, \
    FloatField
from django.db.models.functions import Coalesce, Concat

from app.models import VehicleSpending


def get_earning_subquery(earnings_query_all, start, end):
    return earnings_query_all.filter(
        report_to__range=(start, end),
        vehicle__licence_plate=OuterRef('licence_plate')
    ).values('vehicle__licence_plate').annotate(
        vehicle_earning=Coalesce(Sum('earning'), Decimal(0), output_field=DecimalField())
    )


def get_total_earning_subquery(earnings_query_all):
    return earnings_query_all.filter(
        vehicle__licence_plate=OuterRef('licence_plate')
    ).values('vehicle__licence_plate').annotate(
        vehicle_earning=Coalesce(Sum('earning'), Decimal(0), output_field=DecimalField())
    )


def get_spending_subquery(start, end):
    return VehicleSpending.objects.filter(
        vehicle__licence_plate=OuterRef('licence_plate'),
        created_at__date__range=(start, end)
    ).values('vehicle__licence_plate').annotate(
        total_spending=Coalesce(Sum('amount'), Decimal(0), output_field=DecimalField())
    )


def get_total_spending_subquery():
    return VehicleSpending.objects.filter(
        vehicle__licence_plate=OuterRef('licence_plate')
    ).values('vehicle__licence_plate').annotate(
        total_spending=Coalesce(Sum('amount'), Decimal(0), output_field=DecimalField())
    )


def get_dynamic_fleet():
    dynamic_fleet = {
        'total_kasa': Sum('total_kasa'),
        'full_name': Concat(F("driver__user_ptr__name"),
                            Value(" "),
                            F("driver__user_ptr__second_name"), output_field=CharField()),
        'orders': Sum('total_orders'),
        'orders_rejected': Sum('total_orders_rejected'),
        'average_price': Avg('average_price'),
        'accept_percent': Avg('accept_percent'),
        'road_time': Coalesce(Sum('road_time'), timedelta()),
        'mileage': Sum('mileage'),
        'efficiency': ExpressionWrapper(
            Case(
                When(mileage__gt=0, then=F('total_kasa') / F('mileage')),
                default=Value(0),
                output_field=FloatField()
            ),
            output_field=FloatField()
        )
    }

    return dynamic_fleet
