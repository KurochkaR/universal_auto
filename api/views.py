from collections import defaultdict
from datetime import timedelta

from _decimal import Decimal
from itertools import groupby
from operator import itemgetter

from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Sum, F, OuterRef, Subquery, DecimalField, Avg, Value, CharField, ExpressionWrapper, Case, \
    When, Func, FloatField, Exists, Prefetch, Q, IntegerField, DateField
from django.db.models.functions import Concat, Round, Coalesce, Cast, Extract
from django.forms import DurationField
from django.utils import timezone
from rest_framework import generics
from rest_framework.response import Response

from api.mixins import CombinedPermissionsMixin, ManagerFilterMixin, InvestorFilterMixin
from api.serializers import SummaryReportSerializer, CarEfficiencySerializer, CarDetailSerializer, \
    DriverEfficiencyRentSerializer, InvestorCarsSerializer, ReshuffleSerializer, DriverPaymentsSerializer, \
    DriverEfficiencyFleetRentSerializer, DriverInformationSerializer, NotCompletePaymentsSerializer
from app.models import SummaryReport, CarEfficiency, Vehicle, DriverEfficiency, RentInformation, DriverReshuffle, \
    PartnerEarnings, InvestorPayments, DriverPayments, PaymentsStatus, PenaltyBonus, Penalty, Bonus, \
    DriverEfficiencyFleet, VehicleSpending, Driver, BonusCategory, CustomReport, SalaryCalculation, WeeklyReport, \
    ParkSettings, Schema
from scripts.redis_conn import get_logger
from taxi_service.utils import get_start_end, get_dates


class SummaryReportListView(CombinedPermissionsMixin, generics.ListAPIView):
    serializer_class = SummaryReportSerializer

    def get_queryset(self):
        partner = self.request.user.pk if self.request.user.is_partner() else self.request.user.manager.managers_partner.pk
        start, end, format_start, format_end = get_start_end(self.kwargs['period'])
        start_week, _, _, _ = get_start_end('current_week')
        queryset = ManagerFilterMixin.get_queryset(DriverEfficiency, self.request.user).select_related('driver__user_ptr')
        filtered_qs = queryset.filter(report_from__range=(start, end))
        weekly_bolt_reports = WeeklyReport.objects.filter(
            report_from__range=(start, end), report_to__range=(start, end), partner=partner,
            fleet__name="Bolt").order_by('report_from')

        kasa_bonus = filtered_qs.aggregate(
            kasa=Coalesce(Sum('total_kasa'), Decimal(0)),
            rent_amount=Coalesce(Sum('rent_distance'), Decimal(0)),
            weekly_kasa=Coalesce(Sum('total_kasa', filter=Q(
                driver__schema__salary_calculation=SalaryCalculation.WEEK,
                report_from__range=(start_week, end))), Decimal(0))
        )
        weekly_bonus = 0
        if weekly_bolt_reports.exists():
            weekly_bonus = weekly_bolt_reports.aggregate(bonus=Coalesce(Sum('bonuses'), Decimal(0)))['bonus']
            # custom_bonus = filtered_qs.filter(
            #     report_to__range=(weekly_bolt_reports.last().report_to + timedelta(minutes=1), end)).aggregate(
            #     bonus=Coalesce(Sum('bonuses'), Decimal(0)))['bonus']
            # bonus = weekly_bonus + custom_bonus

        kasa = kasa_bonus['kasa'] + weekly_bonus

        # rent_amount_subquery = Subquery(RentInformation.objects.filter(
        #     report_from__range=(start, end),
        #     driver_id=OuterRef('driver_id')
        # ).values('driver_id').annotate(
        #     rent_amount=Coalesce(Sum('rent_distance'), Decimal(0))
        # ).values('rent_amount'))

        payment_totals = DriverPayments.objects.filter(
            report_to__range=(start, end),
            partner=partner,
        ).aggregate(
            kasa=Coalesce(Sum('kasa', filter=Q(status__in=[PaymentsStatus.CHECKING, PaymentsStatus.PENDING])), Decimal(0)),
            rent_distance=Coalesce(
                Sum('rent_distance', filter=Q(status__in=[PaymentsStatus.CHECKING, PaymentsStatus.PENDING])), Decimal(0)),
            rent=Coalesce(Sum('rent', filter=Q(status=PaymentsStatus.COMPLETED)), Decimal(0)),
        )

        bonus_category, _ = BonusCategory.objects.get_or_create(title='Компенсація холостого пробігу')
        total_compensation_bonus = Bonus.objects.filter(
            created_at__range=(start, end),
            driver_payments__status=PaymentsStatus.COMPLETED,
            driver_payments__partner_id=partner
        ).aggregate(total_spending=Coalesce(Sum('amount'), Decimal(0)),
                    total_amount=Coalesce(Sum('amount', filter=Q(category=bonus_category)), Decimal(0)),
                    )

        total_vehicle_spending = VehicleSpending.objects.filter(
            created_at__range=(start, end),
            partner=partner
        ).aggregate(total_spending=Coalesce(Sum('amount'), Decimal(0)))['total_spending']

        queryset = filtered_qs.values('driver_id').annotate(
            full_name=Concat(
                Func(F("driver__user_ptr__name"), Value(1), Value(1), function='SUBSTRING', output_field=CharField()),
                Value(". "),
                F("driver__user_ptr__second_name"), output_field=CharField()),
            total_kasa_sum=Sum('total_kasa'),
            total_cash_sum=Sum('total_cash'),
            total_card_sum=Sum('total_kasa') - Sum('total_cash'),
            rent_amount=Coalesce(Sum('rent_distance'), Decimal(0)),
            # payment_amount=Subquery(payment_amount_subquery.filter(driver_id=OuterRef('driver_id')).values('payment_amount')),
            weekly_payments=Coalesce(Sum('total_kasa', filter=Q(
                driver__schema__salary_calculation=SalaryCalculation.WEEK,
                report_from__gte=start_week)), Decimal(0))
        )

        # total_dict = queryset.aggregate(total_rent=Coalesce(Sum('rent_amount'), Decimal(0)),
        #                                 total_payment=Coalesce(Sum('payment_amount'), Decimal(0)) + Coalesce(
        #                                     Sum('weekly_payments'), Decimal(0)),
        #                                 sum_rent=Coalesce(Sum('payment_rent'), Decimal(0)),
        #                                 total_distance=Coalesce(Sum('rent_distance'), Value(0)))
        queryset = queryset.exclude(total_kasa_sum=0).order_by('full_name')
        rent_earnings = payment_totals['rent'] - total_compensation_bonus['total_amount']
        return [dict(total_distance=payment_totals['rent_distance'],
                     rent_earnings=rent_earnings,
                     total_rent=kasa_bonus['rent_amount'],
                     kasa=kasa,
                     total_payment=payment_totals['kasa'] + kasa_bonus['weekly_kasa'],
                     total_vehicle_spending=total_vehicle_spending,
                     total_driver_spending=total_compensation_bonus['total_spending'],
                     start=format_start,
                     end=format_end,
                     drivers=queryset)]


class InvestorCarsEarningsView(CombinedPermissionsMixin,
                               generics.ListAPIView):
    serializer_class = InvestorCarsSerializer

    def get_queryset(self):
        start, end, format_start, format_end = get_start_end(self.kwargs['period'])
        queryset = InvestorFilterMixin.get_queryset(InvestorPayments, self.request.user)
        queryset = queryset.filter(report_from__range=(start, end))
        lose_percent = ParkSettings.get_value("LOSE_PERCENT", default=12)
        mileage_subquery = CarEfficiency.objects.filter(
            report_from__range=(start, end),
            investor=self.request.user
        ).select_related('vehicle').values('vehicle__licence_plate').annotate(
            mileage=Sum('mileage'),
            spending=Sum('total_spending'),
            price=F('vehicle__purchase_price'),
            start_count_roi=Case(
                When(vehicle__purchase_date__gt=start, then=F('vehicle__purchase_date')),
                default=start,
                output_field=DateField()),
            days_since_purchase=Extract(end - F('start_count_roi'), 'day'),
            current_price=F('vehicle__purchase_price') -
                          (F('days_since_purchase') / 365) * lose_percent *
                          F('vehicle__purchase_price') / 100,
            start_mileage=Case(
                When(vehicle__purchase_date__gt=start, then=F('vehicle__start_mileage')),
                default=0,
                output_field=DecimalField()
            ),
            total_mileage=F('start_mileage') + F('mileage')
        )

        total_mileage_spending = mileage_subquery.aggregate(
            total_mileage=Coalesce(Sum(F('mileage') + F('start_mileage'), output_field=DecimalField()), Decimal(0)),
            total_spending=Coalesce(Sum('spending', output_field=DecimalField()), Decimal(0)),
            total_investment=Coalesce(Sum('price', output_field=IntegerField()), 0),
            total_actives=Coalesce(Sum('current_price', output_field=DecimalField()), Decimal(0))

        )
        # mileage_info = mileage_subquery.values('vehicle').annotate('mileage')
        # get_logger().info(mileage_info)
        qs = queryset.values('vehicle__licence_plate').annotate(
            licence_plate=F('vehicle__licence_plate'),
            earnings=Sum(F('earning')),
            mileage=Subquery(mileage_subquery.filter(
                vehicle__licence_plate=OuterRef('vehicle__licence_plate')).values('total_mileage'),
                             output_field=DecimalField())
        )
        total_earnings = queryset.aggregate(
            total_earnings=Coalesce(Sum(F('earning')), Decimal(0)))['total_earnings']
        total_investment = total_mileage_spending["total_investment"] if total_mileage_spending[
            "total_investment"] else 1
        roi = ((total_earnings - total_mileage_spending["total_spending"] +
                total_mileage_spending["total_actives"] - total_investment) / total_investment)
        total = dict(total_earnings=total_earnings, total_mileage=total_mileage_spending["total_mileage"],
                     total_spending=total_mileage_spending["total_spending"],
                     roi=roi * 100, )
        # annualized_roi=(pow((1+roi), 1/days_since_purchase) - 1) * 100)
        return [{'start': format_start, 'end': format_end, 'car_earnings': qs, 'totals': total}]


class CarEfficiencyListView(CombinedPermissionsMixin, generics.ListAPIView):
    serializer_class = CarEfficiencySerializer

    def get_queryset(self):
        start, end = get_start_end(self.kwargs['period'])[:2]
        queryset = ManagerFilterMixin.get_queryset(CarEfficiency, self.request.user)
        filtered_qs = queryset.filter(
            report_from__range=(start, end)).select_related('vehicle')
        earning = PartnerEarnings.objects.filter(
            partner=self.request.user,
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
            vehicle_id=F('vehicle__id'),
            average_vehicle=Coalesce(Sum('total_kasa') / Sum('mileage'), Decimal(0)),
            total_earnings=Coalesce(Sum('total_kasa'), Decimal(0)),
            vehicle_brand=F('vehicle__branding__name'),
            branding_trips=Coalesce(Sum('total_brand_trips'), 0)
        )

        mileage_dict = {}
        for item in queryset:
            if item.vehicle.licence_plate not in mileage_dict:
                mileage_dict[item.vehicle.licence_plate] = 0
            mileage_dict[item.vehicle.licence_plate] += item.mileage

        queryset = queryset.filter(vehicle=self.kwargs['vehicle']).order_by("report_from")
        kasa = aggregated_data.get('total_kasa')
        total_mileage = aggregated_data.get('total_mileage')
        average = kasa / total_mileage if total_mileage else Decimal(0)
        dates = sorted(list(set(queryset.values_list("report_from", flat=True))))
        format_dates = []
        for date in dates:
            new_date = timezone.localtime(date).strftime("%d.%m")
            format_dates.append(new_date)

        vehicle_list = [
            {
                item['vehicle__licence_plate']: {
                    "vehicle_id": item['vehicle_id'],
                    "average_eff": round(item['average_vehicle'], 2),
                    "total_earnings": round(item['total_earnings'], 2),
                    "vehicle_brand": item['vehicle_brand'],
                    "branding_trips": item['branding_trips'],
                }
            }
            for item in efficiency_qs

        ]

        response_data = {
            "mileage": mileage_dict,
            "efficiency": list(queryset.values_list("efficiency", flat=True)),
            "dates": format_dates,
            "total_mileage": total_mileage,
            "earning": earning,
            "average_efficiency": average,
            "vehicle_list": vehicle_list
        }
        return Response(response_data)


def get_dynamic_fleet():
    dynamic_fleet = {
        'total_kasa': Sum('total_kasa'),
        'full_name': Concat(F("driver__user_ptr__name"),
                            Value(" "),
                            F("driver__user_ptr__second_name"), output_field=CharField()),
        'total_orders_accepted': Sum('total_orders_accepted'),
        'total_orders_rejected': Sum('total_orders_rejected'),
        'average_price': Avg('average_price'),
        'accept_percent': Avg('accept_percent'),
        'road_time': Coalesce(Sum('road_time'), timedelta()),
        'mileage': Sum('mileage'),
        'efficiency': ExpressionWrapper(
            Case(
                When(mileage__gt=0, then=F('total_kasa') / F('mileage')),
                default=Value(0),
                output_field=DecimalField()
            ),
            output_field=DecimalField()
        )
    }

    return dynamic_fleet


class DriverEfficiencyListView(CombinedPermissionsMixin,
                               generics.ListAPIView):
    serializer_class = DriverEfficiencyRentSerializer

    def get_queryset(self):
        start, end, format_start, format_end = get_start_end(self.kwargs['period'])
        queryset = ManagerFilterMixin.get_queryset(DriverEfficiency, self.request.user)
        filtered_qs = queryset.filter(report_from__range=(start, end))
        dynamic_fleet = get_dynamic_fleet()
        dynamic_fleet['rent_distance'] = Sum(F('rent_distance'))
        qs_efficient = filtered_qs.values('driver_id').annotate(**dynamic_fleet)

        efficient_driver_ids = set(qs_efficient.values_list('driver_id', flat=True))
        reshuffled_drivers = DriverReshuffle.objects.filter(
            swap_time__range=(start, end),
            driver_start__isnull=False,
            partner=self.request.user
        ).exclude(driver_start__id__in=efficient_driver_ids).distinct()

        reshuffled_driver_ids = reshuffled_drivers.values_list('driver_start__id', flat=True)

        reshuffled_drivers_info = Driver.objects.filter(id__in=reshuffled_driver_ids).values(
            'id', 'name', 'second_name'
        )

        additional_drivers_info = [
            {
                'driver_id': driver_info['id'],
                'full_name': f"{driver_info['name']} {driver_info['second_name']}",
                'total_kasa': 0,
                'total_orders_accepted': 0,
                'total_orders_rejected': 0,
                'average_price': 0,
                'accept_percent': 0,
                'road_time': timedelta(),
                'mileage': 0,
                'rent_distance': 0,
                'efficiency': 0
            }
            for driver_info in reshuffled_drivers_info
        ]

        qs = list(qs_efficient) + additional_drivers_info
        return [
            {'start': format_start, 'end': format_end, 'drivers_efficiency': qs}]


class DriverEfficiencyFleetListView(CombinedPermissionsMixin,
                                    generics.ListAPIView):
    serializer_class = DriverEfficiencyFleetRentSerializer

    def get_queryset(self):
        small_aggregators = self.kwargs['aggregators'].split('&')
        aggregators = [aggregator.capitalize() for aggregator in small_aggregators]
        start, end, format_start, format_end = get_start_end(self.kwargs['period'])

        queryset = ManagerFilterMixin.get_queryset(DriverEfficiencyFleet, self.request.user)
        filtered_qs = queryset.filter(report_from__range=(start, end), fleet__name__in=aggregators)
        dynamic_fleet = get_dynamic_fleet()
        dynamic_fleet['fleet_name'] = F('fleet__name')
        qs = filtered_qs.values('driver_id', 'fleet__name').annotate(
            **dynamic_fleet
        )
        qs = sorted(qs, key=itemgetter('full_name'))
        grouped_qs = []
        for key, group in groupby(qs, key=itemgetter('full_name')):
            driver_data = {'full_name': key, 'fleets': []}
            for item in group:
                fleet_data = {
                    item['fleet_name']: {
                        'driver_id': item['driver_id'],
                        'total_kasa': item['total_kasa'],
                        'total_orders_accepted': item['total_orders_accepted'],
                        'total_orders_rejected': item['total_orders_rejected'],
                        'average_price': item['average_price'],
                        'accept_percent': item['accept_percent'],
                        'road_time': item['road_time'],
                        'mileage': item['mileage'],
                        'efficiency': item['efficiency']
                    }
                }
                driver_data['fleets'].append(fleet_data)
            grouped_qs.append(driver_data)
        return [{'start': format_start, 'end': format_end, 'drivers_efficiency': grouped_qs}]


class CarsInformationListView(CombinedPermissionsMixin, generics.ListAPIView):
    serializer_class = CarDetailSerializer

    def get_queryset(self):
        period = self.kwargs['period']
        start, end, format_start, format_end = get_start_end(period)

        if InvestorFilterMixin.get_queryset(Vehicle, self.request.user):
            queryset = InvestorFilterMixin.get_queryset(Vehicle, self.request.user).filter(deleted_at=None).only(
                'licence_plate',
                'purchase_price'
            )
            earnings_query_all = InvestorPayments.objects.all()
        else:
            queryset = ManagerFilterMixin.get_queryset(Vehicle, self.request.user).filter(deleted_at=None).only(
                'licence_plate',
                'purchase_price'
            )
            earnings_query_all = PartnerEarnings.objects.all()

        earning_annotate = {'vehicle_earning': Coalesce(Sum('earning'), 0, output_field=IntegerField())}
        spending_annotate = {'total_spending': Coalesce(Sum('amount'), 0, output_field=IntegerField())}

        if period == 'all_period':
            start = earnings_query_all.first().report_from
            end = earnings_query_all.last().report_to
            format_start = start.strftime("%d.%m.%Y")
            format_end = end.strftime("%d.%m.%Y")

        earning_subquery = earnings_query_all.filter(
            report_to__range=(start, end), vehicle__licence_plate=OuterRef('licence_plate')
        ).values('vehicle__licence_plate').annotate(**earning_annotate)

        total_earning_subquery = earnings_query_all.filter(
            vehicle__licence_plate=OuterRef('licence_plate')
        ).values('vehicle__licence_plate').annotate(**earning_annotate)

        spending_subquery = VehicleSpending.objects.filter(
            created_at__range=(start, end), vehicle__licence_plate=OuterRef('licence_plate')
        ).values('vehicle__licence_plate').annotate(**spending_annotate)

        total_spending_subquery = VehicleSpending.objects.filter(
            vehicle__licence_plate=OuterRef('licence_plate')
        ).values('vehicle__licence_plate').annotate(**spending_annotate)

        earning_subquery_exists = Exists(earning_subquery.filter(vehicle__licence_plate=OuterRef('licence_plate')))
        queryset = queryset.values('licence_plate').annotate(
            price=F('purchase_price'),
            kasa=Case(When(earning_subquery_exists, then=Subquery(earning_subquery.values('vehicle_earning'))),
                      default=Value(0),
                      output_field=IntegerField()),
            total_kasa=Subquery(total_earning_subquery.values('vehicle_earning')),
            spending=Coalesce(
                Subquery(spending_subquery.filter(
                    vehicle__licence_plate=OuterRef('licence_plate')).values('total_spending'),
                         output_field=IntegerField()
                         ),
                Value(0)
            ),
            total_spending=Coalesce(
                Subquery(total_spending_subquery.filter(
                    vehicle__licence_plate=OuterRef('licence_plate')).values('total_spending'),
                         output_field=IntegerField()
                         ),
                Value(0)
            )
        ).annotate(
            start_date=Value(format_start),
            end_date=Value(format_end),
            progress_percentage=ExpressionWrapper(
                Case(
                    When(purchase_price__gt=0, then=Round((F('kasa') - F('spending')) / F('purchase_price') * 100)),
                    default=Value(0),
                    output_field=IntegerField()
                ),
                output_field=IntegerField()
            ),
            total_progress_percentage=ExpressionWrapper(
                Case(
                    When(purchase_price__gt=0,
                         then=Round((F('total_kasa') - F('total_spending')) / F('purchase_price') * 100)),
                    default=Value(0),
                    output_field=IntegerField()
                ),
                output_field=IntegerField()
            )
        )

        return queryset


class DriverReshuffleListView(CombinedPermissionsMixin, generics.ListAPIView):
    serializer_class = ReshuffleSerializer

    def get_queryset(self):
        vehicles = ManagerFilterMixin.get_queryset(Vehicle, self.request.user)
        active_vehicles = vehicles.filter(deleted_at=None).select_related('branding')
        start, end, format_start, format_end = get_start_end(self.kwargs['period'])
        qs = DriverReshuffle.objects.filter(
            swap_vehicle__in=active_vehicles,
            swap_time__range=(start, end)
        ).select_related('driver_start', 'swap_vehicle').annotate(
            licence_plate=F('swap_vehicle__licence_plate'),
            vehicle_id=F('swap_vehicle__pk'),
            driver_name=Concat(
                F("driver_start__user_ptr__second_name"),
                Value(" "),
                F("driver_start__user_ptr__name")),
            driver_id=F('driver_start__pk'),
            dtp_maintenance=F('dtp_or_maintenance'),
            driver_photo=F('driver_start__photo'),
            start_shift=F('swap_time__time'),
            end_shift=F('end_time__time'),
            date=F('swap_time__date'),
            reshuffle_id=F('pk')
        ).values('licence_plate', 'vehicle_id', 'driver_name', 'driver_id', 'driver_photo',
                 'start_shift', 'end_shift',
                 'date', 'reshuffle_id', 'dtp_maintenance').order_by('start_shift')
        sorted_reshuffles = sorted(qs, key=itemgetter('licence_plate'))
        grouped_by_licence_plate = defaultdict(list)
        for key, group in groupby(sorted_reshuffles, key=itemgetter('licence_plate')):
            grouped_by_licence_plate[key].extend(group)

        reshuffles_list = []
        for vehicle in active_vehicles:
            licence_plate = vehicle.licence_plate
            branding_name = vehicle.branding.name if vehicle.branding else None
            reshuffles = grouped_by_licence_plate.get(licence_plate, [])

            reshuffles_list.append({
                "swap_licence": licence_plate,
                "vehicle_brand": branding_name,
                "reshuffles": reshuffles
            })

        return reshuffles_list

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class DriverPaymentsListView(CombinedPermissionsMixin, generics.ListAPIView):
    serializer_class = DriverPaymentsSerializer

    def get_queryset(self):
        qs = ManagerFilterMixin.get_queryset(DriverPayments, self.request.user)
        status = self.kwargs.get('status')

        def get_status(item):
            switcher = {
                'completed': [PaymentsStatus.COMPLETED, PaymentsStatus.FAILED],
                'on_inspection': [PaymentsStatus.CHECKING, PaymentsStatus.INCORRECT],
                'not_closed': [PaymentsStatus.PENDING]
            }
            return switcher.get(item, [])

        if status in ['completed', 'on_inspection', 'not_closed']:
            queryset = qs.filter(status__in=get_status(status))
        else:
            start, end, format_start, format_end = get_start_end(status)
            queryset = qs.filter(report_to__range=(start, end),
                                 status__in=[PaymentsStatus.COMPLETED, PaymentsStatus.FAILED],
                                 )
        driver_vehicle_ids = DriverReshuffle.objects.filter(
            Q(driver_start=OuterRef('driver')) &
            Q(swap_time__gte=OuterRef('report_from')) &
            Q(swap_time__lte=OuterRef('report_to'))
        ).values('swap_vehicle').annotate(vehicles=ArrayAgg('swap_vehicle', distinct=True)).values('vehicles')[:1]
        queryset = queryset.select_related('driver__user_ptr').prefetch_related(
            Prefetch('penaltybonus_set', queryset=PenaltyBonus.objects.all().select_related('vehicle', 'category'),
                     to_attr='prefetched_penaltybonuses')).annotate(
            full_name=Concat(
                F("driver__user_ptr__name"),
                Value(" "),
                F("driver__user_ptr__second_name")),
            driver_vehicles=Subquery(driver_vehicle_ids),
            bonuses=Coalesce(Sum('penaltybonus__amount', filter=Q(penaltybonus__bonus__isnull=False)), Decimal(0)),
            penalties=Coalesce(Sum('penaltybonus__amount', filter=Q(penaltybonus__penalty__isnull=False)), Decimal(0)),
        ).order_by('-report_to', 'driver')
        return queryset


class NotCompletePayments(CombinedPermissionsMixin, generics.ListAPIView):
    serializer_class = NotCompletePaymentsSerializer

    def get_queryset(self):
        qs = ManagerFilterMixin.get_queryset(DriverPayments, self.request.user)
        start, end, format_start, format_end = get_start_end(self.kwargs['period'])
        start_week, _, _, _ = get_start_end('current_week')
        partner_pk = self.request.user.manager.managers_partner.pk if self.request.user.is_manager() else self.request.user.pk
        weekly_drivers = Schema.get_weekly_drivers(partner_pk)
        qs_efficiency = DriverEfficiency.objects.filter(
            report_from__range=(start, end),
            report_from__gte=start_week,
            driver__in=weekly_drivers
        )

        subquery_efficiency = qs_efficiency.filter(driver_id=OuterRef('driver_id')).values('driver_id').annotate(
            not_payment_kasa=Coalesce(Sum('total_kasa'), Decimal(0))
        ).values('not_payment_kasa')

        qs_payments = qs.filter(
            report_from__range=(start, end),
            status__in=[PaymentsStatus.CHECKING, PaymentsStatus.INCORRECT, PaymentsStatus.PENDING]
        ).select_related('driver')

        queryset = qs_payments if qs_payments.exists() else qs_efficiency

        result_qs = queryset.annotate(
                not_payment_kasa=Subquery(subquery_efficiency)
            )
        return result_qs


class DriverInformationListView(CombinedPermissionsMixin, generics.ListAPIView):
    serializer_class = DriverInformationSerializer

    def get_queryset(self):
        driver = ManagerFilterMixin.get_queryset(Driver, self.request.user).filter(deleted_at=None)
        driver_reshuffle = DriverReshuffle.objects.filter(
            swap_time__lte=timezone.localtime(), end_time__gt=timezone.localtime(),
            driver_start=OuterRef('pk')).values_list(
            'swap_vehicle__licence_plate', flat=True)
        queryset = driver.annotate(
            full_name=Concat(
                F("user_ptr__second_name"),
                Value(" "),
                F("user_ptr__name")),
            driver_schema=F('schema__title'),
            vehicle=Coalesce(Subquery(driver_reshuffle[:1]), Value(""), output_field=CharField())
        ).distinct().order_by('full_name')
        return queryset
