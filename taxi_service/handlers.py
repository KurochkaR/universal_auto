import json
from decimal import Decimal

from celery.result import AsyncResult
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import F
from django.http import JsonResponse, HttpResponse
from django.forms.models import model_to_dict
from django.contrib.auth import logout, authenticate
from django.shortcuts import render
from django.template.loader import render_to_string

from app.models import SubscribeUsers, Manager, CustomUser, DriverPayments, Bonus, Penalty, Vehicle, PenaltyBonus, \
    BonusCategory, PenaltyCategory
from taxi_service.forms import MainOrderForm, CommentForm, BonusForm
from taxi_service.utils import (update_order_sum_or_status, restart_order,
                                partner_logout, login_in_investor,
                                send_reset_code,
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
        task = get_session.apply_async(args=[request.user.pk, aggregator, login, password],
                                       queue=f'beat_tasks_{request.user.pk}')
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
            user = authenticate(username=request.user.username, password=password)
            if user is not None and user.is_active:
                user.set_password(new_password)
                user.save()
                logout(request)
                data = {'success': True}
            else:
                data = {'success': False, 'message': 'Password incorrect'}
            json_data = JsonResponse({'data': data}, safe=False)
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
        upd = update_driver_data.apply_async(args=[partner], queue=f'beat_tasks_{partner}')
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
    def handler_add_shift(request):
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

    @staticmethod
    def handler_delete_shift(request):
        action = request.POST.get('action')
        reshuffle_id = request.POST.get('reshuffle_id')

        result = delete_shift(action, reshuffle_id)
        json_data = JsonResponse({'data': result}, safe=False)
        response = HttpResponse(json_data, content_type='application/json')
        return response

    @staticmethod
    def handler_update_shift(request):
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

    @staticmethod
    def handler_upd_payment_status(request):
        all_payments = request.POST.get('allId')
        driver_payments_id = request.POST.get('id')
        status = request.POST.get('status')

        if all_payments:
            for payment_id in all_payments.split(','):
                try:
                    driver_payments = DriverPayments.objects.get(id=payment_id)
                    driver_payments.change_status(status)
                except DriverPayments.DoesNotExist:
                    continue
        else:
            try:
                driver_payments = DriverPayments.objects.get(id=driver_payments_id)
                driver_payments.change_status(status)
            except DriverPayments.DoesNotExist:
                return JsonResponse({'data': 'error', 'message': 'Payment not found'}, status=404)

        json_data = JsonResponse({'data': 'success'})
        response = HttpResponse(json_data, content_type='application/json')
        return response

    @staticmethod
    def handler_add_bonus_or_penalty(request):
        data = request.POST.copy()
        operation_type = data.get('action')
        new_category = data.get('new_category')
        driver_id = data.get('driver_id')
        model_map = {
            'add-bonus': Bonus,
            'add-penalty': Penalty
        }

        model_instance = model_map.get(operation_type)

        if model_instance is None:
            return JsonResponse({'error': 'Invalid operation type'}, status=400)

        payment_id = data.get('idPayments', None)
        form = BonusForm(request.user, payment_id=payment_id,
                         category=data.get('category_type', None), driver_id=driver_id, data=data)
        if form.is_valid():
            if new_category:
                partner = request.user.manager.managers_partner if request.user.is_manager() else request.user.pk
                if operation_type == 'add-bonus':
                    new_category, _ = BonusCategory.objects.get_or_create(title=data.get('new_category', None),
                                                                          partner_id=partner)
                else:
                    new_category, _ = PenaltyCategory.objects.get_or_create(title=data.get('new_category', None),
                                                                            partner_id=partner)

            bonus_data = {"amount": form.cleaned_data['amount'],
                          "description": form.cleaned_data['description'],
                          "vehicle": form.cleaned_data['vehicle'],
                          "category": new_category if new_category else form.cleaned_data['category']}
            if payment_id:
                if DriverPayments.objects.filter(id=payment_id).exists():
                    driver_payments = DriverPayments.objects.filter(id=payment_id)
                    bonus_data["driver_payments"] = driver_payments.first()
                    bonus_data["driver"] = driver_payments.first().driver
                    if operation_type == 'add-bonus':
                        driver_payments.update(earning=F('earning') + Decimal(bonus_data['amount']),
                                               salary=F('salary') + Decimal(bonus_data['amount']))
                    else:
                        driver_payments.update(earning=F('earning') - Decimal(bonus_data['amount']),
                                               salary=F('salary') + Decimal(bonus_data['amount']))
            else:
                bonus_data["driver_id"] = int(driver_id)
            model_instance.objects.create(**bonus_data)
        else:
            errors = {field: form.errors[field][0] for field in form.errors}
            return JsonResponse({'errors': errors}, status=400)

        return JsonResponse({'data': 'success'})

    @staticmethod
    def handler_upd_bonus_penalty(request):
        data = request.POST.copy()
        bonus_id = data.get('bonus_id', None)
        new_category = data.get('new_category', None)
        type_bonus_penalty = data.get('category_type', None)
        driver_id = data.get('driver_id')
        payment_id = data.get('payment_id')
        form = BonusForm(request.user, category=type_bonus_penalty, data=data, payment_id=payment_id,
                         driver_id=driver_id)
        if form.is_valid():

            if new_category:
                partner = request.user.manager.managers_partner if request.user.is_manager() else request.user.pk
                if type_bonus_penalty == 'bonus':
                    new_category, _ = BonusCategory.objects.get_or_create(title=data.get('new_category', None),
                                                                          partner_id=partner)
                else:
                    new_category, _ = PenaltyCategory.objects.get_or_create(title=data.get('new_category', None),
                                                                            partner_id=partner)
            instance = PenaltyBonus.objects.filter(id=bonus_id).first()

            if instance:
                old_amount = instance.amount
                instance.amount = form.cleaned_data['amount']
                instance.description = form.cleaned_data['description']
                instance.vehicle = form.cleaned_data['vehicle']
                instance.category = new_category if new_category else form.cleaned_data['category']
                instance.save(update_fields=['amount', 'description', 'category', 'vehicle'])
                if instance.driver_payments:
                    driver_payments = instance.driver_payments
                    if isinstance(instance, Bonus):
                        driver_payments.earning -= old_amount
                        driver_payments.earning += instance.amount
                    else:
                        driver_payments.earning += old_amount
                        driver_payments.earning -= instance.amount

                    driver_payments.save(update_fields=['earning', 'salary'])

                return JsonResponse({'data': 'success'})
            else:
                return JsonResponse({'error': 'Bonus not found'}, status=404)
        else:
            errors = {field: form.errors[field][0] for field in form.errors}
            return JsonResponse({'errors': errors}, status=400)

    @staticmethod
    def handler_delete_bonus_penalty(request):
        data = request.POST
        bonus_id = data.get('id', None)
        instance = PenaltyBonus.objects.filter(id=bonus_id).first()
        if instance:
            driver_payments = instance.driver_payments
            if driver_payments:
                if isinstance(instance, Bonus):
                    driver_payments.earning -= instance.amount
                else:
                    driver_payments.earning += instance.amount
                driver_payments.save(update_fields=['earning', 'salary'])
            instance.delete()
            return JsonResponse({'data': 'success'})
        else:
            return JsonResponse({'error': 'Bonus not found'}, status=404)

    @staticmethod
    def handler_calculate_payments(request):
        data = request.POST
        payment = DriverPayments.objects.get(pk=int(data.get('payment')))
        payment.earning = round(payment.kasa * Decimal(int(data.get('rate'))/100) - payment.cash
                           - payment.rent + payment.get_bonuses() - payment.get_penalties(), 2)
        payment.rate = Decimal(data.get('rate'))
        payment.save(update_fields=['earning', 'salary', 'rate'])
        response = {"earning": payment.earning, "rate": payment.rate}
        return JsonResponse(response)

    @staticmethod
    def handle_unknown_action():
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
        if not request.user.is_authenticated:
            raise PermissionDenied("Authentication required")
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
    def handle_render_bonus_form(request):
        user = request.user
        bonus_id = request.GET.get('bonus_penalty')
        category_type = request.GET.get('type')
        driver_id = request.GET.get('driver_id')
        try:
            if bonus_id:
                instance = PenaltyBonus.objects.filter(pk=bonus_id).first()
                payment_id = instance.driver_payments_id
                bonus_form = BonusForm(user, payment_id=payment_id, category=category_type, instance=instance,
                                       driver_id=driver_id)
            else:
                payment_id = request.GET.get('payment')
                bonus_form = BonusForm(user, payment_id=payment_id, category=category_type, driver_id=driver_id)
        except ValidationError:
            return JsonResponse({
                                    "data": "За водієм не закріплено жодного автомобіля! Для додавання бонусу або штрафу створіть зміну водію!"},
                                status=404)

        form_html = render_to_string('dashboard/_bonus-penalty-form.html', {'bonus_form': bonus_form})

        return JsonResponse({"data": form_html})

    @staticmethod
    def handle_unknown_action():
        return JsonResponse({"data": "i'm here now"}, status=400)
