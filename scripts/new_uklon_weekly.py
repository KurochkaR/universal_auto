
from auto.tasks import calculate_vehicle_earnings


def run():
    calculate_vehicle_earnings.delay(1, "2023-11-12")