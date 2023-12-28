import json
from decimal import Decimal

from celery.result import AsyncResult
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse, HttpResponse
from django.forms.models import model_to_dict
from django.contrib.auth import logout

from app.models import SubscribeUsers, Manager, CustomUser, DriverPayments, Bonus, Penalty, Earnings, PaymentsStatus
from taxi_service.forms import MainOrderForm, CommentForm
from taxi_service.utils import (update_order_sum_or_status, restart_order,
                                partner_logout, login_in_investor,
                                change_password_investor, send_reset_code,
                                active_vehicles_gps, order_confirm,
                                check_aggregators, add_shift, delete_shift, upd_shift)

from auto.tasks import update_driver_data, get_session


class PostRequestHandler:
    @staticmethod
    def handler_order_form(request):
        order_form = MainOrderForm(request.POST)
        if order_form.is_valid():
            save_form = order_form.save(
                payment=request.POST.get('payment_method'),
                on_time=request.POST.get('order_time')
            )
            order_dict = model_to_dict(save_form)
            json_data = json.dumps(order_dict, cls=DjangoJSONEncoder)
            return JsonResponse({'data': json_data}, safe=False)
        else:
            return JsonResponse(order_form.errors, status=400)

    @staticmethod
    def handler_subscribe_form(request):
        email = request.POST.get('email')

        obj, created = SubscribeUsers.objects.get_or_create(email=email)

        if created:
            return JsonResponse({'success': True})
        return JsonResponse({'success': False})

    @staticmethod
    def handler_comment_form(request):
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment_form.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse(
                {'success': False, 'errors': 'Щось пішло не так!'})

    @staticmethod
    def handler_update_order(request):
        id_order = request.POST.get('idOrder')
        action = request.POST.get('action')

        update_order_sum_or_status(id_order, action)

        return JsonResponse({}, status=200)

    @staticmethod
    def handler_restarting_order(request):
        id_order = request.POST.get('idOrder')
        car_delivery_price = request.POST.get('carDeliveryPrice', 0)
        action = request.POST.get('action')
        restart_order(id_order, car_delivery_price, action)

        return JsonResponse({}, status=200)

    @staticmethod
    def handler_success_login(request):
        aggregator = request.POST.get('aggregator')
        login = request.POST.get('login')
        password = request.POST.get('password')
        task = get_session.delay(request.user.pk, aggregator, login=login, password=password)
        json_data = JsonResponse({'task_id': task.id}, safe=False)
        response = HttpResponse(json_data, content_type='application/json')

        return response

    @staticmethod
    def handler_handler_logout(request):
        aggregator = request.POST.get('aggregator')
        partner_logout(aggregator, request.user.pk)

        return JsonResponse({}, status=200)

    @staticmethod
    def handler_success_login_investor(request):
        login = request.POST.get('login')
        password = request.POST.get('password')

        success_login = login_in_investor(request, login, password)
        json_data = JsonResponse({'data': success_login}, safe=False)
        response = HttpResponse(json_data, content_type='application/json')
        return response

    @staticmethod
    def handler_logout_investor(request):
        logout(request)
        return JsonResponse({'logged_out': True})

    @staticmethod
    def handler_change_password(request):
        if request.POST.get('action') == 'change_password':
            password = request.POST.get('password')
            new_password = request.POST.get('newPassword')
            user_email = request.user.email

            change = change_password_investor(request, password, new_password, user_email)
            json_data = JsonResponse({'data': change}, safe=False)
            response = HttpResponse(json_data, content_type='application/json')
            return response

        if request.POST.get('action') == 'send_reset_code':
            email = request.POST.get('email')
            user = CustomUser.objects.filter(email=email).first()

            if user:
                user_login = user.username
                code = send_reset_code(email, user_login)
                json_data = JsonResponse({'code': code, 'success': True}, safe=False)
                response = HttpResponse(json_data, content_type='application/json')
                return response
            else:
                response = HttpResponse(json.dumps({'success': False}), content_type='application/json')
                return response

        if request.POST.get('action') == 'update_password':
            email = request.POST.get('email')
            new_password = request.POST.get('newPassword')
            user = CustomUser.objects.filter(email=email).first()
            if user:
                user.set_password(new_password)
                user.save()
                response = HttpResponse(json.dumps({'success': True}), content_type='application/json')
                return response
            else:
                response = HttpResponse(json.dumps({'success': False}), content_type='application/json')
                return response

    @staticmethod
    def handler_update_database(request):
        if request.user.is_partner():
            partner = request.user.pk
        else:
            manager = Manager.objects.get(pk=request.user.pk)
            partner = manager.managers_partner.pk
        upd = update_driver_data.delay(partner)
        json_data = JsonResponse({'task_id': upd.id}, safe=False)
        response = HttpResponse(json_data, content_type='application/json')
        return response

    @staticmethod
    def handler_free_access(request):
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        response_data = {'success': False, 'error': 'Ви вже підписались'}
        phone = phone.replace(' ', '').replace('-', '')
        user, created = SubscribeUsers.objects.get_or_create(phone_number=phone,
                                                             defaults={"name": name})
        if created:
            response_data = {'success': True}

        json_data = JsonResponse(response_data, safe=False)
        response = HttpResponse(json_data, content_type='application/json')
        return response

    def handler_add_shift(self, request):
        user = request.user
        partner = Manager.objects.get(pk=user.pk).managers_partner if user.is_manager() else user
        licence_plate = request.POST.get('vehicle_licence')
        date = request.POST.get('date')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        driver_id = request.POST.get('driver_id')
        recurrence = request.POST.get('recurrence')

        result = add_shift(licence_plate, date, start_time, end_time, driver_id, recurrence, partner)
        json_data = JsonResponse({'data': result}, safe=False)
        response = HttpResponse(json_data, content_type='application/json')
        return response

    def handler_delete_shift(self, request):
        action = request.POST.get('action')
        reshuffle_id = request.POST.get('reshuffle_id')

        result = delete_shift(action, reshuffle_id)
        json_data = JsonResponse({'data': result}, safe=False)
        response = HttpResponse(json_data, content_type='application/json')
        return response

    def handler_update_shift(self, request):
        action = request.POST.get('action')
        licence_id = request.POST.get('vehicle_licence')
        date = request.POST.get('date')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        driver_id = request.POST.get('driver_id')
        reshuffle_id = request.POST.get('reshuffle_id')

        result = upd_shift(action, licence_id, start_time, end_time, date, driver_id, reshuffle_id)
        json_data = JsonResponse({'data': result}, safe=False)
        response = HttpResponse(json_data, content_type='application/json')
        return response

    def handler_update_payments(self, request):
        driver_payments_id = request.POST.get('id')
        bonus_amount = request.POST.get('bonusAmount')
        bonus_description = request.POST.get('bonusDescription')
        penalty_amount = request.POST.get('penaltyAmount')
        penalty_description = request.POST.get('penaltyDescription')

        driver_payments = DriverPayments.objects.get(id=driver_payments_id)

        if bonus_amount:
            bonus = Bonus.objects.create(
                amount=bonus_amount, description=bonus_description, driver_payments=driver_payments
            )
            driver_payments.earning += Decimal(bonus.amount)

        if penalty_amount:
            penalty = Penalty.objects.create(
                amount=penalty_amount, description=penalty_description, driver_payments=driver_payments
            )
            driver_payments.earning -= Decimal(penalty.amount)

        driver_payments.save()

        json_data = JsonResponse({'data': 'success'}, safe=False)
        response = HttpResponse(json_data, content_type='application/json')
        return response

    def handler_confirm_payments(self, request):
        driver_payments_id = request.POST.get('id')
        driver_payments = DriverPayments.objects.get(id=driver_payments_id)
        driver_payments.change_status(PaymentsStatus.PENDING)

        json_data = JsonResponse({'data': 'success'}, safe=False)
        response = HttpResponse(json_data, content_type='application/json')
        return response

    def handler_cancel_payments(self, request):
        driver_payments_id = request.POST.get('id')
        driver_payments = DriverPayments.objects.get(id=driver_payments_id)
        driver_payments.change_status(PaymentsStatus.CHECKING)

        json_data = JsonResponse({'data': 'success'}, safe=False)
        response = HttpResponse(json_data, content_type='application/json')
        return response

    @staticmethod
    def handler_unknown_action():
        return JsonResponse({}, status=400)


class GetRequestHandler:
    @staticmethod
    def handle_active_vehicles_locations():
        active_vehicle_locations = active_vehicles_gps()
        json_data = JsonResponse({'data': active_vehicle_locations}, safe=False)
        response = HttpResponse(json_data, content_type='application/json')
        return response

    @staticmethod
    def handle_order_confirm(request):
        id_order = request.GET.get('id_order')
        driver = order_confirm(id_order)
        json_data = JsonResponse({'data': driver}, safe=False)
        response = HttpResponse(json_data, content_type='application/json')
        return response

    @staticmethod
    def handle_check_aggregators(request):
        aggregators, fleets = check_aggregators(request.user)
        json_data = JsonResponse({'data': aggregators, 'fleets': fleets}, safe=False)
        response = HttpResponse(json_data, content_type='application/json')
        return response

    @staticmethod
    def handle_check_task(request):
        upd = AsyncResult(request.GET.get('task_id'))
        answer = upd.get()[1] if upd.ready() else 'in progress'
        json_data = JsonResponse({'data': answer}, safe=False)
        response = HttpResponse(json_data, content_type='application/json')
        return response

    @staticmethod
    def handle_unknown_action():
        return JsonResponse({}, status=400)
