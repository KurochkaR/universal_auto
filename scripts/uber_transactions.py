from datetime import datetime, timedelta, time

from _decimal import Decimal
from django.db.models import Sum
from django.db.models.functions import TruncWeek
from django.utils import timezone

from app.models import SummaryReport, Driver, DriverPayments, PaymentsStatus, PartnerEarnings, Payments, CustomReport
from app.uklon_sync import UklonRequest


def run():


    # List of fields to copy
    fields_to_copy = ['report_from',
                      'report_to',
                      'fleet_id',
                      'total_amount_without_fee',
                      'total_amount_cash',
                      'total_amount_on_card',
                      'total_amount',
                      'total_rides',
                      'total_distance',
                      'tips',
                      'bonuses',
                      'fee',
                      'fares',
                      'cancels',
                      'compensations',
                      'refunds',
                      'partner_id',
                      'vehicle_id',
                      'driver_id']

    # Get queryset of records from the source model
    source_records = Payments.objects.filter(report_from__lt=datetime(2023,12,10))

    # Create a list to hold instances of the destination model
    destination_records = []

    # Iterate over the queryset and create instances for bulk creation
    for source_record in source_records:
        # Create an instance of the destination model
        destination_record = CustomReport()

        # Copy fields from source to destination using setattr
        for field in fields_to_copy:
            setattr(destination_record, field, getattr(source_record, field))
        setattr(destination_record, 'polymorphic_ctype_id', 123)
        # Append the destination record to the list
        destination_record.save()
