from collections import defaultdict
from datetime import timedelta

from _decimal import Decimal
from itertools import groupby
from operator import itemgetter

from django.db.models import Sum, F, OuterRef, Subquery, DecimalField, Avg, Value, CharField, ExpressionWrapper, Case, \
    When, Func, FloatField, Exists
from django.db.models.functions import Concat, Round, Coalesce, TruncTime
from rest_framework import generics
from rest_framework.response import Response

from api.mixins import CombinedPermissionsMixin, ManagerFilterMixin, InvestorFilterMixin
from api.serializers import SummaryReportSerializer, CarEfficiencySerializer, CarDetailSerializer, \
    DriverEfficiencyRentSerializer, InvestorCarsSerializer, ReshuffleSerializer, DriverPaymentsSerializer
from app.models import SummaryReport, CarEfficiency, Vehicle, DriverEfficiency, RentInformation, DriverReshuffle, \
    PartnerEarnings, InvestorPayments, DriverPayments, PaymentsStatus
from taxi_service.utils import get_start_end


class SummaryReportListView(CombinedPermissionsMixin,
                            generics.ListAPIView):
    serializer_class = SummaryReportSerializer

    @staticmethod
    def format_name(name):
        if len(name) > 17:
            half_length = len(name) // 2
            name = name[:half_length] + '-\n' + name[half_length:]
        return name

    def get_queryset(self):
        start, end, format_start, format_end = get_start_end(self.kwargs['period'])
        queryset = ManagerFilterMixin.get_queryset(SummaryReport, self.request.user)
        filtered_qs = queryset.filter(report_from__range=(start, end))
        rent_amount_subquery = RentInformation.objects.filter(
            report_from__range=(start, end)
        ).values('driver_id').annotate(
            rent_amount=Sum('rent_distance')
        )
        queryset = filtered_qs.values('driver_id').annotate(
            full_name=Concat(
                Func(F("driver__user_ptr__name"), Value(1), Value(1), function='SUBSTRING', output_field=CharField()),
                Value(". "),
                F("driver__user_ptr__second_name"), output_field=CharField()),
            total_kasa=Sum('total_amount_without_fee'),
            total_cash=Sum('total_amount_cash'),
            total_card=Sum('total_amount_without_fee') - Sum('total_amount_cash'),
            rent_amount=Subquery(rent_amount_subquery.filter(
                driver_id=OuterRef('driver_id')).values('rent_amount'), output_field=DecimalField())
        )
        total_rent = queryset.aggregate(total_rent=Sum('rent_amount'))['total_rent'] or 0
        queryset = queryset.exclude(total_kasa=0).order_by('full_name')
        return [{'total_rent': total_rent, 'start': format_start, 'end': format_end, 'drivers': queryset}]


class InvestorCarsEarningsView(CombinedPermissionsMixin,
                               generics.ListAPIView):
    serializer_class = InvestorCarsSerializer

    def get_queryset(self):
        start, end, format_start, format_end = get_start_end(self.kwargs['period'])
        queryset = InvestorFilterMixin.get_queryset(InvestorPayments, self.request.user)
        filtered_qs = queryset.filter(report_from__range=(start, end))
        mileage_subquery = CarEfficiency.objects.filter(
            report_from__range=(start, end)
        ).values('vehicle__licence_plate').annotate(
            mileage=Sum('mileage'),
            spending=Sum('total_spending')
        )
        total_mileage_spending = mileage_subquery.aggregate(
            total_mileage=Coalesce(Sum('mileage', output_field=DecimalField()), Decimal(0)),
            total_spending=Coalesce(Sum('spending', output_field=DecimalField()), Decimal(0))
        )
        qs = filtered_qs.values('vehicle__licence_plate').annotate(
            licence_plate=F('vehicle__licence_plate'),
            earnings=Sum(F('earning')),
            mileage=Subquery(mileage_subquery.filter(
                vehicle__licence_plate=OuterRef('vehicle__licence_plate')).values('mileage'),
                             output_field=DecimalField())
        )
        total_earnings = filtered_qs.aggregate(
            total_earnings=Coalesce(Sum(F('earning')), Decimal(0)))['total_earnings']
        total = {
            "total_earnings": total_earnings,
            "total_mileage": total_mileage_spending["total_mileage"],
            "total_spending": total_mileage_spending["total_spending"]
        }
        return [{'start': format_start, 'end': format_end, 'car_earnings': qs, 'totals': total}]


class CarEfficiencyListView(CombinedPermissionsMixin,
                            generics.ListAPIView):
    serializer_class = CarEfficiencySerializer

    def get_queryset(self):
        start, end = get_start_end(self.kwargs['period'])[:2]
        queryset = ManagerFilterMixin.get_queryset(CarEfficiency, self.request.user)
        filtered_qs = queryset.filter(
            report_from__range=(start, end))
        earning = PartnerEarnings.objects.filter(
            report_from__range=(start, end)
        ).aggregate(earning=Coalesce(Sum('earning'), Decimal(0)))['earning']
        return filtered_qs, earning

    def list(self, request, *args, **kwargs):
        queryset, earning = self.get_queryset()
        aggregated_data = queryset.aggregate(
            total_kasa=Coalesce(Sum('total_kasa'), Decimal(0)),
            total_mileage=Coalesce(Sum('mileage'), Decimal(0))
        )
        efficiency_qs = queryset.values('vehicle__licence_plate').distinct().filter(mileage__gt=0).annotate(
            average_vehicle=Coalesce(Sum('total_kasa') / Sum('mileage'), Decimal(0)))
        queryset = queryset.filter(vehicle=self.kwargs['vehicle']).order_by("report_from")
        kasa = aggregated_data.get('total_kasa')
        total_mileage = aggregated_data.get('total_mileage')
        average = kasa / total_mileage if total_mileage else Decimal(0)
        dates = sorted(list(set(queryset.values_list("report_from", flat=True))))
        format_dates = []
        for date in dates:
            new_date = date.strftime("%d.%m")
            format_dates.append(new_date)
        efficiency_dict = {
            "mileage": list(queryset.values_list("mileage", flat=True)),
            "efficiency": list(queryset.values_list("efficiency", flat=True)),
            "average_eff": {item['vehicle__licence_plate']: round(item['average_vehicle'], 2) for item in
                            efficiency_qs},
        }
        response_data = {
            "vehicles": efficiency_dict,
            "dates": format_dates,
            "total_mileage": total_mileage,
            "kasa": kasa,
            "earning": earning,
            "average_efficiency": average
        }
        return Response(response_data)


class DriverEfficiencyListView(CombinedPermissionsMixin,
                               generics.ListAPIView):
    serializer_class = DriverEfficiencyRentSerializer

    def get_queryset(self):
        start, end, format_start, format_end = get_start_end(self.kwargs['period'])
        queryset = ManagerFilterMixin.get_queryset(DriverEfficiency, self.request.user)
        filtered_qs = queryset.filter(report_from__range=(start, end)).exclude(total_orders=0)
        qs = filtered_qs.values('driver_id').annotate(
            total_kasa=Sum('total_kasa'),
            full_name=Concat(F("driver__user_ptr__name"),
                             Value(" "),
                             F("driver__user_ptr__second_name"), output_field=CharField()),
            orders=Sum('total_orders'),
            average_price=Avg('average_price'),
            accept_percent=Avg('accept_percent'),
            road_time=Coalesce(Sum('road_time'), timedelta()),
            mileage=Sum('mileage'),
            efficiency=ExpressionWrapper(
                Case(
                    When(mileage__gt=0, then=F('total_kasa') / F('mileage')),
                    default=Value(0),
                    output_field=FloatField()
                ),
                output_field=FloatField()
            ),
        )

        return [{'start': format_start, 'end': format_end, 'drivers_efficiency': qs}]


class CarsInformationListView(CombinedPermissionsMixin,
                              generics.ListAPIView):
    serializer_class = CarDetailSerializer

    def get_queryset(self):
        investor_queryset = InvestorFilterMixin.get_queryset(Vehicle, self.request.user)
        if investor_queryset:
            queryset = investor_queryset
            earning_subquery = InvestorPayments.objects.all().values('vehicle__licence_plate').annotate(
                vehicle_earning=Coalesce(Sum('earning'), Decimal(0)),
            )
            queryset = queryset.values('licence_plate').annotate(
                price=F('purchase_price'),
                kasa=Subquery(earning_subquery.filter(
                    vehicle__licence_plate=OuterRef('licence_plate')).values('vehicle_earning'),
                              output_field=DecimalField()
                              ),
                spending=Coalesce(Sum('vehiclespending__amount'), Decimal(0))
            ).annotate(
                progress_percentage=ExpressionWrapper(
                    Case(
                        When(purchase_price__gt=0, then=Round((F('kasa') / F('purchase_price')) * 100)),
                        default=Value(0),
                        output_field=DecimalField(max_digits=5, decimal_places=2)
                    ),
                    output_field=DecimalField(max_digits=5, decimal_places=2)
                )
            )
        else:
            queryset = ManagerFilterMixin.get_queryset(Vehicle, self.request.user)
            earning_subquery = PartnerEarnings.objects.filter(
                vehicle__licence_plate=OuterRef('licence_plate')
            ).values('vehicle__licence_plate').annotate(
                vehicle_earning=Coalesce(Sum('earning'), Value(0), output_field=DecimalField())
            )
            earning_subquery_exists = Exists(earning_subquery.filter(vehicle__licence_plate=OuterRef('licence_plate')))
            queryset = queryset.values('licence_plate').annotate(
                price=F('purchase_price'),
                kasa=Case(When(earning_subquery_exists, then=Subquery(earning_subquery.values('vehicle_earning'))),
                          default=Value(0),
                          output_field=DecimalField()
                          ),
                spending=Coalesce(Sum('vehiclespending__amount'), Decimal(0))
            ).annotate(
                progress_percentage=ExpressionWrapper(
                    Case(
                        When(purchase_price__gt=0,
                             then=Round(((F('kasa') - F('spending')) / F('purchase_price')) * 100)),
                        default=Value(0),
                        output_field=DecimalField(max_digits=4, decimal_places=1)
                    ),
                    output_field=DecimalField(max_digits=4, decimal_places=1)
                )
            )
        return queryset


class DriverReshuffleListView(CombinedPermissionsMixin, generics.ListAPIView):
    serializer_class = ReshuffleSerializer

    def get_queryset(self):
        vehicles = ManagerFilterMixin.get_queryset(Vehicle, self.request.user)
        qs = DriverReshuffle.objects.filter(
            swap_vehicle__in=vehicles,
            swap_time__range=(self.kwargs['start_date'], self.kwargs['end_date'])
        ).annotate(
            licence_plate=F('swap_vehicle__licence_plate'),
            vehicle_id=F('swap_vehicle__pk'),
            driver_name=Concat(
                F("driver_start__user_ptr__name"),
                Value(" "),
                F("driver_start__user_ptr__second_name")),
            driver_id=F('driver_start__pk'),
            driver_photo=F('driver_start__photo'),
            start_shift=F('swap_time__time'),
            end_shift=F('end_time__time'),
            date=F('swap_time__date'),
            reshuffle_id=F('pk')
        ).values('licence_plate', 'vehicle_id', 'driver_name', 'driver_id', 'driver_photo', 'start_shift', 'end_shift',
                 'date', 'reshuffle_id').order_by('start_shift')
        sorted_reshuffles = sorted(qs, key=itemgetter('licence_plate'))
        grouped_by_licence_plate = defaultdict(list)
        for key, group in groupby(sorted_reshuffles, key=itemgetter('licence_plate')):
            grouped_by_licence_plate[key].extend(group)

        for vehicle in vehicles:
            if vehicle.licence_plate not in grouped_by_licence_plate:
                grouped_by_licence_plate[vehicle.licence_plate] = []
        reshuffles_list = []
        for licence_plate, reshuffles in grouped_by_licence_plate.items():
            reshuffle_data = {
                "swap_licence": licence_plate,
                "reshuffles": reshuffles
            }
            reshuffles_list.append(reshuffle_data)
        return reshuffles_list

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class DriverPaymentsListView(CombinedPermissionsMixin, generics.ListAPIView):
    serializer_class = DriverPaymentsSerializer

    def get_queryset(self):
        qs = ManagerFilterMixin.get_queryset(DriverPayments, self.request.user)

        period = self.kwargs.get('period')

        if not period:
            queryset = (qs.filter(
                status__in=[PaymentsStatus.CHECKING, PaymentsStatus.PENDING],
            )).order_by('report_to')
        else:
            start, end, format_start, format_end = get_start_end(period)
            queryset = (qs.filter(
                report_to__range=(start, end),
                status__in=[PaymentsStatus.COMPLETED, PaymentsStatus.FAILED],
            )).order_by('report_to')

        return queryset
