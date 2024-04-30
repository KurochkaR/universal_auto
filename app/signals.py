from datetime import datetime, time, timedelta
from time import sleep

from celery.result import AsyncResult
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F
from django.utils import timezone
from django_celery_beat.models import PeriodicTask
from telegram import ParseMode
from telegram.error import BadRequest

from app.uagps_sync import UaGpsSynchronizer
from auto.tasks import send_on_job_application_on_driver, check_time_order, search_driver_for_order, \
    calculate_vehicle_earnings, calculate_vehicle_spending, calculate_failed_earnings
from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from app.models import Driver, StatusChange, JobApplication, ParkSettings, Partner, Order, DriverSchemaRate, \
    Schema, DriverPayments, InvestorPayments, FleetOrder, FleetsDriversVehiclesRate, Fleet, Manager, Vehicle
from auto_bot.handlers.driver.keyboards import detail_payment_kb
from auto_bot.handlers.driver_manager.utils import create_driver_payments, message_driver_report
from auto_bot.handlers.order.keyboards import inline_reject_order
from auto_bot.handlers.order.static_text import client_order_info
from auto_bot.handlers.order.utils import check_vehicle
from auto_bot.main import bot
from scripts.redis_conn import redis_instance
from scripts.settings_for_park import standard_rates, settings_for_partner


@receiver(post_delete, sender=Driver)
def calculate_fired_driver(sender, instance, **kwargs):
    if instance.schema and instance.schema.is_weekly():
        end = timezone.localtime().date()
        if end.weekday():
            start = end - timedelta(days=end.weekday())
            data = create_driver_payments(start, end, instance, instance.schema, delete=True)[0]
            DriverPayments.objects.get_or_create(report_from=start,
                                                 report_to=end,
                                                 driver=instance,
                                                 defaults=data)


@receiver(post_save, sender=Vehicle)
def new_vehicle_notification(sender, instance, created, **kwargs):
    if created:
        managers = Manager.objects.filter(managers_partner=instance.partner)
        if managers.count() == 1:
            instance.manager = managers.first()
            instance.save(update_fields=['manager'])
        elif managers.count() > 1:
            message_text = f"У вас новий автомобіль {instance.license_plate}. Будь ласка, призначте йому менеджера."
            bot.send_message(chat_id=instance.partner.chat_id, text=message_text)


@receiver(post_save, sender=DriverPayments)
@receiver(post_save, sender=InvestorPayments)
def create_payments(sender, instance, created, **kwargs):
    if instance.is_completed():
        if isinstance(instance, DriverPayments):
            calculate_vehicle_earnings.apply_async(kwargs={"payment_id":instance.pk})
        else:
            calculate_vehicle_spending.apply_async(kwargs={"payment_id":instance.pk})
    elif instance.is_pending():
        if isinstance(instance, DriverPayments):
            message = message_driver_report(instance)
            keyboard = detail_payment_kb(instance.pk)
            try:
                sleep(0.5)
                bot.send_message(chat_id=instance.driver.manager.chat_id, text=message, reply_markup=keyboard,
                                 parse_mode=ParseMode.HTML)
                bot.send_message(chat_id=instance.driver.chat_id, text=message, reply_markup=keyboard,
                                 parse_mode=ParseMode.HTML)
            except BadRequest as e:
                if e.message == 'Chat not found':
                    bot.send_message(chat_id=ParkSettings.get_value("DEVELOPER_CHAT_ID"),
                                     text=f"Driver {instance.driver} Не вірний чат айді")
                else:
                    bot.send_message(chat_id=ParkSettings.get_value("DEVELOPER_CHAT_ID"),
                                     text=f"У {instance.driver} відсутній чат айді")
        else:
            pass
    # InvestorMassage
    elif instance.is_failed():
        calculate_failed_earnings.apply_async(kwargs={"payment_id":instance.pk})


@receiver(post_save, sender=Partner)
def create_park_settings(sender, instance, created, **kwargs):
    if created:
        for key, value in settings_for_partner.items():
            ParkSettings.objects.create(key=key, value=value[0], description=value[1], partner=instance)
        for key, values in standard_rates.items():
            for value in values:
                DriverSchemaRate.objects.create(period=key, threshold=value[0], rate=value[1], partner=instance)


# @receiver(pre_save, sender=Driver)
# def create_status_change(sender, instance, **kwargs):
#     try:
#         old_instance = Driver.objects.get(pk=instance.pk)
#     except ObjectDoesNotExist:
#         # new instance, ignore
#         return
#     if old_instance.driver_status != instance.driver_status:
#         # update the end time of the previous status change
#         prev_status_changes = StatusChange.objects.filter(driver=instance, end_time=None)
#         prev_status_changes.update(end_time=timezone.now(), duration=F('end_time') - F('start_time'))
#         if prev_status_changes.count() > 1:
#             bot.send_message(chat_id=ParkSettings.get_value("DEVELOPER_CHAT_ID"),
#                              text=f'Multiple status for driver {instance.id} deleted')
#         # driver_status has changed, create new status change
#         status_change = StatusChange(
#             driver=instance,
#             name=instance.driver_status,
#             vehicle=instance.vehicle,
#             start_time=timezone.now(),
#         )
#         status_change.save()


@receiver(pre_delete, sender=Partner)
@receiver(pre_delete, sender=Schema)
def remove_tasks_for_deleted_schema(sender, instance, **kwargs):
    partner_id = instance.pk if isinstance(instance, Partner) else instance.partner
    tasks = PeriodicTask.objects.filter(args__contains=[partner_id, instance.pk])
    for task in tasks:
        result = AsyncResult(task.celery_task_id)
        result.revoke(terminate=True)
        task.delete()


@receiver(post_save, sender=JobApplication)
def run_add_drivers_task(sender, instance, created, **kwargs):
    if created:
        send_on_job_application_on_driver.delay(instance.id)


@receiver(post_save, sender=Order)
def take_order_from_client(sender, instance, **kwargs):
    update = False
    if not instance.checked:
        if instance.status_order == Order.WAITING:
            instance.checked = True
            instance.save()
            search_driver_for_order.delay(instance.pk)
            return
        elif all([instance.status_order == Order.ON_TIME, instance.sum, instance.type_order == Order.STANDARD_TYPE]):
            client_msg = redis_instance().hget(instance.chat_id_client, 'client_msg')
            redis_instance().hdel(instance.chat_id_client, 'time_order')
            if client_msg:
                bot.delete_message(chat_id=instance.chat_id_client, message_id=client_msg)
            else:
                update = True
            client_msg = bot.send_message(chat_id=instance.chat_id_client,
                                          text=client_order_info(instance, update),
                                          reply_markup=inline_reject_order(instance.pk))
            redis_instance().hset(instance.chat_id_client, 'client_msg', client_msg.message_id)
        check_time_order.delay(instance.pk)
        # g_id = ParkSettings.get_value("GOOGLE_ID_ORDER_CALENDAR")
        # if g_id:
        #     description = f"Адреса посадки: {instance.address}\n" \
        #                   f"Місце прибуття: {instance.to_address}\n" \
        #                   f"Спосіб оплати: {instance.payment}\n" \
        #                   f"Номер телефону: {instance.phone}\n"
        #     create_event(
        #         f"Замовлення {instance.pk}",
        #         description,
        #         datetime_with_timezone(instance.order_time),
        #         datetime_with_timezone(instance.order_time),
        #         ParkSettings.get_value("GOOGLE_ID_ORDER_CALENDAR")
        #     )
