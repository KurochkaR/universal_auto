import os

import jwt
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q

from django.urls import reverse
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
from django.views.generic import View, TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from api.views import CarsInformationListView
from taxi_service.forms import SubscriberForm, MainOrderForm
from taxi_service.handlers import PostRequestHandler, GetRequestHandler
from taxi_service.seo_keywords import seo_index, seo_park_page
from app.models import Driver, Vehicle, CustomUser
from auto_bot.main import bot


class IndexView(TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["seo_keywords"] = seo_index
        context["subscribe_form"] = SubscriberForm()
        return context


class PostRequestView(View):
    def post(self, request):
        handler = PostRequestHandler()
        action = request.POST.get("action")

        method = {
            "order": handler.handler_order_form,
            "subscribe": handler.handler_subscribe_form,
            "send_comment": handler.handler_comment_form,
            "order_sum": handler.handler_update_order,
            "user_opt_out": handler.handler_update_order,
            "increase_price": handler.handler_restarting_order,
            "continue_search": handler.handler_restarting_order,
            "login": handler.handler_success_login,
            "logout": handler.handler_handler_logout,
            "login_invest": handler.handler_success_login_investor,
            "logout_invest": handler.handler_logout_investor,
            "change_password": handler.handler_change_password,
            "send_reset_code": handler.handler_change_password,
            "update_password": handler.handler_change_password,
            "upd_database": handler.handler_update_database,
            "free_access_or_consult": handler.handler_free_access,
            "add_shift": handler.handler_add_shift,
            "delete_shift": handler.handler_delete_shift,
            "delete_all_shift": handler.handler_delete_shift,
            "update_shift": handler.handler_update_shift,
            "update_all_shift": handler.handler_update_shift,
            "upd-payments": handler.handler_update_payments,
            "upd-status-payment": handler.handler_upd_payment_status,
        }

        if action in method:
            return method[action](request)
        else:
            return handler.handler_unknown_action(request)


class GetRequestView(View):
    def get(self, request):
        handler = GetRequestHandler()
        action = request.GET.get("action")

        method = {
            "active_vehicles_locations": handler.handle_active_vehicles_locations,
            "order_confirm": handler.handle_order_confirm,
            "aggregators": handler.handle_check_aggregators,
            "check_task": handler.handle_check_task,
        }

        if action in method:
            return method[action](request)
        else:
            return handler.handle_unknown_action(request)


class AutoParkView(TemplateView):
    template_name = "auto-park.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["seo_keywords"] = seo_park_page
        context["subscribe_form"] = SubscriberForm()
        return context


class InvestmentView(View):
    def get(self, request):
        return render(request, "investment.html", {"subscribe_form": SubscriberForm()})


class DriversView(TemplateView):
    template_name = "drivers.html"
    paginate_by = 8

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        drivers = Driver.objects.all()
        paginator = Paginator(drivers, self.paginate_by)
        page_number = self.request.GET.get("page")
        page_obj = paginator.get_page(page_number)
        context["subscribe_form"] = SubscriberForm()
        context["page_obj"] = page_obj
        return context


class BaseDashboardView(LoginRequiredMixin, TemplateView):
    login_url = "index"

    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_superuser:
            return redirect(reverse('admin:index'))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        user = self.request.user
        context = super().get_context_data(**kwargs)
        context["investor_group"] = user.is_investor()
        context["partner_group"] = user.is_partner()
        context["manager_group"] = user.is_manager()

        return context


class DashboardView(BaseDashboardView):
    template_name = "dashboard/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_manager():
            context["get_all_vehicle"] = Vehicle.objects.filter(manager=user)
            context["get_all_driver"] = Driver.objects.get_active(manager=user)

        elif user.is_partner():
            context["get_all_vehicle"] = Vehicle.objects.filter(partner=user)
            context["get_all_driver"] = Driver.objects.get_active(partner=user)
        return context


class DashboardPaymentView(BaseDashboardView):
    template_name = "dashboard/dashboard-payments.html"


class DashboardVehicleView(BaseDashboardView):
    template_name = "dashboard/dashboard-vehicle.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["car_piggy_bank"] = CarsInformationListView.get_queryset(self)
        return context


class DashboardDriversView(BaseDashboardView):
    template_name = "dashboard/dashboard-drivers.html"


class DashboardCalendarView(BaseDashboardView):
    template_name = "dashboard/dashboard-calendar.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_manager():
            context["get_all_vehicle"] = Vehicle.objects.filter(manager=user)
            context["get_all_driver"] = Driver.objects.get_active(manager=user)

        elif user.is_partner():
            context["get_all_vehicle"] = Vehicle.objects.filter(partner=user)
            context["get_all_driver"] = Driver.objects.get_active(partner=user)
        return context


class GoogleAuthView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(GoogleAuthView, self).dispatch(request, *args, **kwargs)

    def post(self, request):
        credential_data = request.POST.get("credential")
        data = jwt.decode(credential_data, options={"verify_signature": False})
        email = data["email"].lower()
        redirect_url = reverse("index")

        if email:
            user = CustomUser.objects.filter(email=email).first()
            if user:
                user.backend = "django.contrib.auth.backends.ModelBackend"
                login(request, user)
                redirect_url = reverse("dashboard")
            else:
                return redirect(reverse("index") + "?signed_in=false")

        return HttpResponseRedirect(redirect_url)


class SendToTelegramView(View):
    def get(self, request, *args, **kwargs):
        chat_id = os.environ.get("TELEGRAM_BOT_CHAT_ID")

        telegram_link = f"https://t.me/{bot.username}?start={chat_id}"

        return HttpResponseRedirect(telegram_link)


def blog(request):
    return render(request, "blog.html")


def why(request):
    return render(request, "why.html", {"subscribe_form": SubscriberForm()})


def agreement(request):
    return render(request, "agreement.html", {"subscribe_form": SubscriberForm()})


class RobotsView(TemplateView):
    template_name = "robots.txt"
    content_type = "text/plain"


class SitemapView(TemplateView):
    template_name = "sitemap.xml"
    content_type = "application/xml"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
