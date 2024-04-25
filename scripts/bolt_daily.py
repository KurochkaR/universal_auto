from app.models import Driver
from app.uagps_sync import UaGpsSynchronizer
from auto_bot.handlers.driver_manager.utils import get_time_for_task
from taxi_service.utils import get_dates, get_start_end


def run(*args):

    start, end = get_dates('last_week')
    print(start, end)