import requests

from app.ninja_sync import NinjaFleet


def run(*args):
    car_efficiencies = CarEfficiency.objects.all()
    for car_efficiency in car_efficiencies:
        car_efficiency.investor = car_efficiency.vehicle.investor_car
        car_efficiency.save()
    print("CarEfficiency updated")
