from datetime import timedelta, datetime
from app.models import ParkSettings, FleetOrder, VehicleGPS
from scripts.conversion import get_coordinates_from_place, haversine


def run(*args):
    start = datetime.now() - timedelta(days=1)
    api_key = ParkSettings.get_value('GOOGLE_API_KEY')
    orders = FleetOrder.objects.filter(fleet="Uklon", accepted_time__gte=start, state=FleetOrder.COMPLETED)
    for order in orders:
        try:
            if order.price / order.distance < 10:
                print(order.id)
                address = order.destination
                lat, lon = get_coordinates_from_place(address, api_key)
                coordinates = VehicleGPS.objects.filter(vehicle=order.vehicle, created_at__gte=order.accepted_time)
                for coordinate in coordinates:
                    distance = haversine(float(coordinate.lat), float(coordinate.lon),
                                         float(lat), float(lon))
                    if distance <= 0.1:
                        print(order.finish_time)
                        print(coordinate.created_at)
                        break
                break
        except:
            pass



