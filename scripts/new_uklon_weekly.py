from django.utils import timezone

from app.bolt_sync import BoltRequest


def run():
    day = timezone.localtime()
    BoltRequest.objects.get(partner=1).save_report(day, day, 2)