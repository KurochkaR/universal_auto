from django.contrib.auth.decorators import login_required
from django.urls import path
from taxi_service.views import *
from django.views.i18n import JavaScriptCatalog

urlpatterns = [
    path('', login_required(IndexView.as_view()), name='index'),
    path('accounts/login/', IndexView.as_view(), name='login'),
    path('post-request/', PostRequestView.as_view(), name='post_request'),
    path('get-request/', GetRequestView.as_view(), name='get_request'),
    path('auto-park/', AutoParkView.as_view(), name='auto-park'),
    path('investment/', InvestmentView.as_view(), name='investment'),
    path('charging-stations/', ChargingStationsView.as_view(), name='charging_stations'),
    path('price/', PriceView.as_view(), name='price'),

    path('dashboard/', login_required(DashboardView.as_view()), name='dashboard'),
    path('dashboard/drivers/', login_required(DriversView.as_view()), name='drivers'),
    path('dashboard/driver/<int:pk>/', login_required(DriverDetailView.as_view()), name='driver_detail'),
    path('dashboard/vehicle/', login_required(DashboardVehicleView.as_view()), name='dashboard_vehicle'),
    path('dashboard/drivers-efficiency/', login_required(DashboardDriversEfficiencyView.as_view()),
         name='dashboard_efficiency'),
    path('dashboard/drivers-payment/', login_required(DashboardPaymentView.as_view()), name='dashboard_payment'),
    path('dashboard/driver-calendar/', login_required(DashboardCalendarView.as_view()), name='dashboard_calendar'),

    path('sign-in/', GoogleAuthView.as_view(), name='sign_in'),
    path('send-to-telegram/', SendToTelegramView.as_view(), name='send_to_telegram'),

    path('blog/', blog, name='blog'),
    path('why/', why, name='why'),
    path('user-agreement/', agreement, name='user_agreement'),
    path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),

    path('robots.txt', TemplateView.as_view(template_name="robots.txt", content_type="text/plain"), name="robots_file"),
    path('sitemap.xml', TemplateView.as_view(template_name="sitemap.xml", content_type="text/xml"),
         name="sitemap_file"),
]
