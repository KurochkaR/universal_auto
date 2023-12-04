# Generated by Django 4.1 on 2023-11-30 09:00

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0065_alter_investor_managers_alter_manager_managers_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='investor',
            name='email',
        ),
        migrations.RemoveField(
            model_name='investor',
            name='first_name',
        ),
        migrations.RemoveField(
            model_name='investor',
            name='id',
        ),
        migrations.RemoveField(
            model_name='investor',
            name='last_name',
        ),
        migrations.RemoveField(
            model_name='investor',
            name='password',
        ),
        migrations.RemoveField(
            model_name='investor',
            name='role',
        ),
        migrations.RemoveField(
            model_name='manager',
            name='calendar',
        ),
        migrations.RemoveField(
            model_name='manager',
            name='chat_id',
        ),
        migrations.RemoveField(
            model_name='manager',
            name='email',
        ),
        migrations.RemoveField(
            model_name='manager',
            name='first_name',
        ),
        migrations.RemoveField(
            model_name='manager',
            name='id',
        ),
        migrations.RemoveField(
            model_name='manager',
            name='last_name',
        ),
        migrations.RemoveField(
            model_name='manager',
            name='login',
        ),
        migrations.RemoveField(
            model_name='manager',
            name='password',
        ),
        migrations.RemoveField(
            model_name='manager',
            name='role',
        ),
        migrations.RemoveField(
            model_name='partner',
            name='chat_id',
        ),
        migrations.RemoveField(
            model_name='partner',
            name='id',
        ),
        migrations.RemoveField(
            model_name='partner',
            name='role',
        ),
        migrations.AlterField(
            model_name='investor',
            name='customuser_ptr',
            field=models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='manager',
            name='customuser_ptr',
            field=models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='partner',
            name='customuser_ptr',
            field=models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(choices=[('CLIENT', 'Клієнт'), ('DRIVER', 'Водій'), ('DRIVER_MANAGER', 'Менеджер водіїв'), ('SERVICE_STATION_MANAGER', 'Сервісний менеджер'), ('SUPPORT_MANAGER', 'Менеджер підтримки'), ('PARTNER', 'Власник'), ('INVESTOR', 'Інвестор')], default='CLIENT', max_length=25),
        ),
    ]
