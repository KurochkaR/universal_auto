# Generated by Django 4.1 on 2023-11-29 09:21

from django.conf import settings
import django.contrib.auth.models
from django.db import migrations, models
import django.db.models.deletion


def add_user_ptr(apps, schema_editor):
    Investor = apps.get_model('app', 'Investor')
    Manager = apps.get_model('app', 'Manager')
    Partner = apps.get_model('app', 'Partner')
    CustomUser = apps.get_model('app', 'CustomUser')
    ParkSettings = apps.get_model('app', 'ParkSettings')

    for obj in Investor.objects.all():
        user = CustomUser.objects.create_user(
            username=obj.email,
            password=obj.password,
            is_staff=True,
            is_active=True,
            is_superuser=False,
            first_name=obj.first_name,
            last_name=obj.last_name,
            email=obj.email
        )
        obj.user_ptr = user
        obj.save()

    for obj in Manager.objects.all():
        user = CustomUser.objects.create_user(
            username=obj.email,
            password=obj.password,
            is_staff=True,
            is_active=True,
            is_superuser=False,
            first_name=obj.first_name,
            last_name=obj.last_name,
            email=obj.email
        )
        obj.user_ptr = user
        obj.save()

    for obj in Partner.objects.all():
        name, passw = ParkSettings.objects.get(key="USERNAME", partner=obj.id).value, ParkSettings.objects.get(key="PASSWORD", partner=obj.id).value
        user = CustomUser.objects.create_user(
            username=name,
            password=passw,
            is_staff=True,
            is_active=True,
            is_superuser=False,
        )
        obj.user_ptr = user
        obj.save()


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0064_alter_customuser_groups_and_more'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='investor',
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='manager',
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='partner',
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.RenameField(
            model_name='investor',
            old_name='partner',
            new_name='investors_partner',
        ),
        migrations.RenameField(
            model_name='manager',
            old_name='partner',
            new_name='managers_partner',
        ),
        migrations.AddField(
            model_name='investor',
            name='customuser_ptr',
            field=models.OneToOneField(auto_created=True, null=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=False, serialize=False, to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='manager',
            name='customuser_ptr',
            field=models.OneToOneField(auto_created=True, null=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=False, serialize=False, to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='partner',
            name='customuser_ptr',
            field=models.OneToOneField(auto_created=True, null=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=False, serialize=False, to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
        migrations.RunPython(add_user_ptr)
    ]
