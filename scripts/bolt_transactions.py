from app.models import FleetsDriversVehiclesRate


def run():
    fleets = FleetsDriversVehiclesRate.objects.filter(driver=26).values_list("fleet", flat=True)
    print(fleets)

