import sys

from django.db.models import Sum
from django.db.models.functions import TruncWeek

print(sys.path)
sys.path.append('app/')
from app.models import CarEfficiency


def run():
    records = CarEfficiency.objects.all()

    weekly_aggregates = records.annotate(
        week_start=TruncWeek('report_from'),
    ).values(
        'week_start'
    ).annotate(
        total=Sum('total_kasa')
    ).order_by('week_start')

    # Print or use the aggregated data as needed
    for aggregate in weekly_aggregates:
        print(aggregate['week_start'].date())
        print(aggregate['total'])
