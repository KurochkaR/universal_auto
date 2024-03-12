import os

import jwt
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, F

from django.urls import reverse
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.views.generic import View, TemplateView, DetailView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from api.views import CarsInformationListView
from taxi_service.forms import SubscriberForm, MainOrderForm, BonusForm
from taxi_service.handlers import PostRequestHandler, GetRequestHandler
from taxi_service.seo_keywords import *
from app.models import Driver, Vehicle, CustomUser, BonusCategory, PenaltyCategory, DriverReshuffle, Bonus, Penalty
from auto_bot.main import bot


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
            "add-bonus": handler.handler_add_bonus_or_penalty,
            "add-penalty": handler.handler_add_bonus_or_penalty,
            "upd-status-payment": handler.handler_upd_payment_status,
            "upd_bonus_penalty": handler.handler_upd_bonus_penalty,
            "delete_bonus_penalty": handler.handler_delete_bonus_penalty,
            "calculate-payments": handler.handler_calculate_payments,
            "switch_cash": handler.handler_switch_cash,
            "switch_auto_cash": handler.handler_switch_auto_cash,
            "change_cash_percent": handler.handler_change_cash_percent,
            "create-new-payment": handler.handler_create_payment
        }

        if action in method:
            return method[action](request)
        else:
            return handler.handle_unknown_action()


class GetRequestView(View):
    def get(self, request):
        handler = GetRequestHandler()
        action = request.GET.get("action")
        method = {
            "active_vehicles_locations": handler.handle_active_vehicles_locations,
            "order_confirm": handler.handle_order_confirm,
            "aggregators": handler.handle_check_aggregators,
            "check_task": handler.handle_check_task,
            "render_bonus": handler.handle_render_bonus_form,
            "render_bonus_driver": handler.handle_render_bonus_form,
            "check_cash": handler.handle_check_cash,
        }

        if action in method:
            return method[action](request)
        else:
            return handler.handle_unknown_action()


class BaseContextView(TemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["subscribe_form"] = SubscriberForm()
        context["sentry_cdn"] = os.environ.get("SENTRY_CDN_FRONTEND")
        return context


class IndexView(BaseContextView, TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["seo_keywords"] = seo_index
        context["seo_title"] = seo_index_title
        context["seo_description"] = seo_description
        return context


class AutoParkView(BaseContextView, TemplateView):
    template_name = "auto-park.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["seo_keywords"] = seo_park_page
        context["seo_title"] = seo_park_page_title
        context["seo_description"] = seo_description_park_page
        return context


class InvestmentView(BaseContextView, TemplateView):
    template_name = "investment.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["seo_keywords"] = seo_investment_page
        context["seo_title"] = seo_investment_page_title
        context["seo_description"] = seo_description_investment_page
        return context


class ChargingStationsView(BaseContextView, TemplateView):
    template_name = "charging-station.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # context["seo_keywords"] = seo_charging_stations_page
        # context["seo_title"] = seo_charging_stations_page_title
        # context["seo_description"] = seo_description_charging_stations_page
        return context


class PriceView(BaseContextView, TemplateView):
    template_name = "price.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # context["seo_keywords"] = seo_price_page
        # context["seo_title"] = seo_price_page_title
        # context["seo_description"] = seo_description_price_page
        return context


# DASHBOARD VIEWS ->


class BaseDashboardView(LoginRequiredMixin, TemplateView):
    login_url = "index"

    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_superuser:
            return redirect(reverse('admin:index'))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        user = self.request.user
        context = super().get_context_data(**kwargs)
        context["get_all_vehicle"] = None
        context["get_all_driver"] = None

        if user.is_manager():
            context["get_active_vehicle"] = Vehicle.objects.get_active(manager=user).order_by("licence_plate")
            context["get_all_driver"] = Driver.objects.get_active(manager=user).order_by("second_name")
            context["get_all_vehicle"] = Vehicle.objects.filter(manager=user).order_by("licence_plate")
            context["get_vehicle_eff"] = Vehicle.objects.filter(carefficiency__vehicle_id=F('id'),
                                                                manager=user).distinct()

        elif user.is_partner():
            context["get_all_vehicle"] = Vehicle.objects.filter(partner=user).order_by("licence_plate")
            context["get_all_driver"] = Driver.objects.get_active(partner=user).order_by("second_name")
            context["get_active_vehicle"] = Vehicle.objects.get_active(partner=user).order_by("licence_plate")
            context["get_vehicle_eff"] = Vehicle.objects.filter(carefficiency__vehicle_id=F('id'),
                                                                partner=user).distinct()

        context["investor_group"] = user.is_investor()
        context["partner_group"] = user.is_partner()
        context["manager_group"] = user.is_manager()
        context["sentry_cdn"] = os.environ.get("SENTRY_CDN_FRONTEND")
        return context


class DashboardView(BaseDashboardView):
    template_name = "dashboard/dashboard.html"


class DashboardPaymentView(BaseDashboardView):
    template_name = "dashboard/dashboard-payments.html"


class DashboardVehicleView(BaseDashboardView):
    template_name = "dashboard/dashboard-vehicle.html"


class DashboardDriversEfficiencyView(BaseDashboardView):
    template_name = "dashboard/dashboard-efficiency.html"


class DashboardCalendarView(BaseDashboardView):
    template_name = "dashboard/dashboard-calendar.html"


class DriversView(BaseDashboardView):
    template_name = "dashboard/drivers.html"


class DriverDetailView(DetailView):
    model = Driver
    template_name = 'dashboard/driver_detail.html'

    def get_context_data(self, **kwargs):
        driver_id = self.kwargs['pk']
        driver_reshuffle = DriverReshuffle.objects.filter(
            swap_time__lte=timezone.localtime(), end_time__gt=timezone.localtime(),
            driver_start=driver_id).first()

        context = super().get_context_data(**kwargs)
        context["driver_bonus"] = Bonus.objects.filter(driver=driver_id, driver_payments__isnull=True)
        context["driver_penalty"] = Penalty.objects.filter(driver=driver_id, driver_payments__isnull=True)
        context["investor_group"] = self.request.user.is_investor()
        context["partner_group"] = self.request.user.is_partner()
        context["manager_group"] = self.request.user.is_manager()
        context["vehicle"] = {
            "number": driver_reshuffle.swap_vehicle.licence_plate if driver_reshuffle else "Не назначено",
            "name": driver_reshuffle.swap_vehicle.name if driver_reshuffle else ""
        }
        return context


# OTHER PAGES VIEWS ->

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
