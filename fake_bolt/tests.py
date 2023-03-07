from django.contrib.auth.models import User
from django.test import Client, RequestFactory, TestCase

from fake_bolt.views import DailyWeeklyBoltView, daily_bolt, weekly_bolt


class UserAuthenticateTest(TestCase):
    def setUp(self):
        user = User.objects.create_user("TestBolt", "test@test.com", "qwerty")
        user.save()
        self.c = Client()
        self.factory = RequestFactory()

    def tearDown(self) -> None:
        user = User.objects.get(username="TestBolt")
        user.delete()

    def test_user_authenticate_ok(self):
        """input correct login and password"""
        response = self.c.post(
            "/fake_bolt/login/",
            {"Username": "TestBolt", "Password": "qwerty"},
        )
        self.assertEqual(response.status_code, 302, "Error status code")
        self.assertRedirects(response, '/fake_bolt/company/58225/reports/dayly/')

    def test_user_authenticate_err(self):
        """input wrong password"""
        response = self.c.post(
            "/fake_bolt/login/",
            {"Username": "TestBolt", "Password": "wrongpass"},
        )
        self.assertEqual(response.status_code, 302, "Error status code")
        self.assertRedirects(response, '/fake_bolt/login/')

    def test_get_login_page(self):
        response = self.c.get("/fake_bolt/login/")
        self.assertEqual(response.status_code, 200, "Error status code")
        content = str(response.content)
        self.assertIn('name="Username"', content, "Error load loging page")
        self.assertIn('name="Password"', content, "Error load loging page")

    def test_daily_page(self):
        request = self.factory.get(
            "/fake_bolt/company/58225/reports/dayly/"
        )
        user = User.objects.get(username="TestBolt")
        request.user = user
        response = daily_bolt(request)
        self.assertEqual(response.status_code, 200, "Error status code")

    def test_weekly_page(self):
        request = self.factory.get(
            "/fake_bolt/company/58225/reports/weekly/"
        )
        user = User.objects.get(username="TestBolt")
        request.user = user
        response = weekly_bolt(request)
        self.assertEqual(response.status_code, 200, "Error status code")

    def test_get_report_csv(self, date_str='2022W37'):
        request = self.factory.get(
            f"/fake_bolt/company/58225/reports/weekly/{date_str}"
        )
        user = User.objects.get(username="TestBolt")
        request.user = user
        response = DailyWeeklyBoltView.as_view()(request, date_str=date_str)
        self.assertEqual(response.status_code, 200, "Error status code")
        self.assertEqual(
            response.headers["Content-Type"], "text/csv", "Error. Return not csv"
        )
