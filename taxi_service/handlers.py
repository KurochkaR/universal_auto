import json

from celery.result import AsyncResult
from django.contrib.auth import logout
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.models import User
from django.forms.models import model_to_dict


from app.models import SubscribeUsers
from taxi_service.forms import MainOrderForm, CommentForm
from taxi_service.utils import (update_order_sum_or_status, restart_order,
                                partner_logout, login_in_investor,
                                change_password_investor, send_reset_code,
                                active_vehicles_gps, order_confirm,
                                check_aggregators)

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
            user = User.objects.filter(email=email).first()

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
            user = User.objects.filter(email=email).first()
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
        partner = request.user.pk if request.user.is_partner() else request.user.managers_partner
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
