from taxi_service.utils import get_dates


def run(*args):
    start, end = get_dates('current_month')
    print((end-start).days/365)
