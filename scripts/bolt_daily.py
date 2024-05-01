from datetime import datetime

from django.db.models import Q
from django.utils import timezone

from app.models import Driver, DriverPayments, FleetOrder, Fleet, Partner
from app.uagps_sync import UaGpsSynchronizer
from auto_bot.handlers.driver_manager.utils import get_time_for_task
from taxi_service.utils import get_dates, get_start_end


def run(*args):
    partner = Partner.objects.get(pk=1)
    print(list(partner.manager_set.values_list('chat_id', flat=True)))


