from app.uagps_sync import UaGpsSynchronizer


def run():
    UaGpsSynchronizer.objects.create(name="Gps", base_url="https://uagps.net/")
