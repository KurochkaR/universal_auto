# Generated by Django 4.1 on 2024-04-04 08:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0093_driverpayments_bolt_screen_alter_earnings_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehicle',
            name='investor_schema',
            field=models.CharField(blank=True, choices=[('Equal_share', 'Рівномірна'), ('Proportional', 'Пропорційна')], max_length=15, null=True, verbose_name='Схема інвестора'),
        ),
    ]
