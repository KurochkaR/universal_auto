import csv
import urllib
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, HttpResponseRedirect, HttpResponse, reverse
from django.contrib.auth import login, authenticate
from django.views import View


def bolt_login(request):
    if request.method == "POST":
        username = request.POST['Username']
        password = request.POST['Password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse('bolt-daily'))
        else:
            messages.warning(request, "Невірні облікові дані")
            return HttpResponseRedirect(reverse('bolt-login'))
    else:
        return render(request, 'bolt_login.html')


@login_required(login_url='/fake_bolt/login/')
def daily_bolt(request):
    return render(request, 'bolt_daily.html')


class DailyWeeklyBoltView(LoginRequiredMixin, View):
    name_rows_all = "Водій, Телефон водія, Період, Загальний тариф, Плата за скасування, Авторизаційцний платіж (платіж), Авторизаційцний платіж (відрахування), Додатковий збір, Комісія Bolt, Поїздки за готівку (зібрана готівка), Сума знижки Bolt за готівкові поїздки, Водійський бонус, Компенсації, Повернення коштів, Чайові, Тижневий баланс, Онлайн години, Утилізація\n"
    name_rows = "Ім'я водія, Телефон водія, Дата, Оплата підтверджена, Посадка, Метод оплати, Запитано, Ціна поїздки, Авторизаційцний платіж, Додатковий збір, Плата за скасування, Чайові, Статус замовлення, Модель авто, Номерний знак авто, , , ,\n"
    test_all = """Усі водії","","День 2022-11-15","4986.00","0.00","0.00","0.00","0.00","-1246.50","-1449.00","330.00","0.00","0.00","0.00","10.00","2300.50","20.27","67.87"
    "Євген Волонкович","+380937645871","День 2022-11-15","0.00","0.00","0.00","0.00","0.00","0.00","0.00","0.00","0.00","","0.00","0.00","0.00","0.00","0.00"
    "Анатолій Мухін","+380936503350","День 2022-11-15","0.00","0.00","0.00","0.00","0.00","0.00","0.00","0.00","0.00","","0.00","0.00","0.00","0.00","0.00"
    "Володимир Золотніков","+380669692591","День 2022-11-15","275.00","0.00","0.00","0.00","0.00","-68.75","-144.00","40.00","0.00","","0.00","0.00","62.25","3.36","25.48\n"""
    test_daily = """"Олег Філіппов","+380671887096","2022-11-15","15:35","вулиця Феодори Пушиної, 4, Киев, Украина","Готівка","15:19","102.00","0.00","0.00","0.00","0.00","Завершено","BYD e2","AA3410YA","","",""
    "Юрій Філіппов","+380502428878","2022-11-15","15:24","Івана Виговського вулиця 5/1, Київ","Готівка","15:01","143.00","0.00","0.00","0.00","0.00","Завершено","BYD e2","AA4314YA","","",""
    "Олег Філіппов","+380671887096","2022-11-15","15:17","Січових Стрільців вулиця 86-88, Київ 04050","Платіж Bolt","15:05","122.00","0.00","0.00","0.00","0.00","Завершено","BYD e2","AA3410YA","","",""
    "Олег Філіппов","+380671887096","2022-11-15","15:04","Багговутівська вулиця 28, Киев","Готівка","14:58","60.00","0.00","0.00","0.00","0.00","Завершено","BYD e2","AA3410YA","","","""""

    login_url = '/fake_bolt/login/'

    @staticmethod
    def get(request, date_str):
        try:
            datetime.strptime(date_str, '%d.%m.%Y')
            filename = f"Щоденний звіт Bolt – {date_str} – Kyiv Fleet 03_232 park Universal-auto.csv"
        except ValueError:
            filename = f"Щотижневий звіт Bolt – {date_str} – Kyiv Fleet 03_232 park Universal-auto.csv"
        response = HttpResponse(
            DailyWeeklyBoltView.name_rows_all + DailyWeeklyBoltView.test_all + "\n" + DailyWeeklyBoltView.name_rows + DailyWeeklyBoltView.test_daily,
            content_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename={urllib.parse.quote(filename)}"
            }, )
        return response


@login_required(login_url='/fake_bolt/login/')
def weekly_bolt(request):
    return render(request, 'bolt_weekly.html')
