
def run(*args):
    def update_reports(apps, schema_editor):
        Payments = apps.get_model('app', 'Payments')
        CustomReport = apps.get_model('app', 'CustomReport')
        DriverReport = apps.get_model('app', 'DriverReport')
        Summary = apps.get_model('app', 'SummaryReport')
        FleetDriver = apps.get_model('app', 'FleetsDriversVehiclesRate')
        Fleet = apps.get_model('app', 'Fleet')
        ContentType = apps.get_model('contenttypes', 'ContentType')

        # for payment in Payments.objects.all():
        #     payment.driver = FleetDriver.objects.get(driver_external_id=payment.rider_id).driver
        #     payment.vendor = Fleet.objects.get(name=payment.vendor_name, partner=payment.partner)
        #     payment.save(update_fields=['driver', 'vendor'])
        #     fields = [field.name for field in payment._meta.fields if field.name not in ['driverreport_ptr', 'id', 'vendor_name', 'full_name', 'rider_id','vendor']]
        #     field_values = {field: getattr(payment, field) for field in fields}
        #     field_values['polymorphic_ctype'] = ContentType.objects.get_for_model(payment)
        #     new_report = DriverReport.objects.create(**field_values)
        #     payment.driverreport_ptr = new_report
        #     payment.save()

        # for payment in CustomReport.objects.all():
        #     payment.driver = FleetDriver.objects.get(driver_external_id=payment.rider_id).driver
        #     payment.vendor = Fleet.objects.get(name=payment.vendor_name, partner=payment.partner)
        #     payment.save(update_fields=['driver', 'vendor'])
        #     fields = [field.name for field in payment._meta.fields if field.name not in ['driverreport_ptr', 'id', 'vendor_name', 'full_name', 'rider_id','vendor']]
        #     field_values = {field: getattr(payment, field) for field in fields}
        #     field_values['polymorphic_ctype'] = ContentType.objects.get_for_model(payment)
        #     new_report = DriverReport.objects.create(**field_values)
        #     payment.driverreport_ptr = new_report
        #     payment.save()

        # for sum_report in Summary.objects.all():
        #     fields = [field.name for field in sum_report._meta.fields if field.name not in ['driverreport_ptr', 'id']]
        #     field_values = {field: getattr(sum_report, field) for field in fields}
        #     field_values['polymorphic_ctype'] = ContentType.objects.get_for_model(sum_report)
        #     new_report = DriverReport.objects.create(**field_values)