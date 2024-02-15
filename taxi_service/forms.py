from django import forms
from django.core.validators import MinValueValidator, RegexValidator, MinLengthValidator
from django.db.models import Q
from django.forms import ModelForm
from django.utils import timezone
from django.utils.html import format_html

from app.models import Order, SubscribeUsers, User, Comment, Bonus, BonusCategory, Vehicle, Category, DriverPayments, \
    DriverReshuffle
from django.utils.translation import gettext_lazy as _


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('comment',)
        widgets = {'comment': forms.Textarea(attrs={'rows': 5, 'cols': 50})}


class PhoneInput(forms.NumberInput):
    input_type = 'tel'

    def build_attrs(self, attrs, extra_attrs=None, **kwargs):
        attrs = super().build_attrs(attrs, extra_attrs, **kwargs)
        attrs['pattern'] = r'^[\d+]*$'
        attrs['onkeypress'] = 'return event.charCode >= 48 && event.charCode <= 57 || event.charCode == 46'
        attrs['oninput'] = r"this.value = this.value.replace(/[^0-9.]/g, '');".replace("'", r'"')
        return attrs


class MainOrderForm(ModelForm):
    class Meta:
        model = Order
        fields = (
            'from_address', 'to_the_address', 'phone_number',
            'order_time', 'latitude', 'longitude', 'to_latitude',
            'to_longitude', 'status_order', 'sum', 'distance_google',
        )

        widgets = {
            'from_address': forms.TextInput(attrs={
                'id': 'address', 'class': 'form-control', 'placeholder': _('Звідки вас забрати?'),
                'style': 'font-size: medium'}),
            'to_the_address': forms.TextInput(attrs={
                'id': 'to_address', 'class': 'form-control', 'placeholder': _('Куди їдемо?'),
                'style': 'font-size: medium'}),
            'phone_number': PhoneInput(attrs={
                'id': 'phone', 'class': 'form-control', 'placeholder': _('Номер телефону'),
                'style': 'font-size: medium'}),
            'order_time': forms.TextInput(attrs={
                'id': 'delivery_time', 'class': 'form-control',
                'placeholder': _('На яку годину? формат HH:MM(напр. 18:45)'), 'style': 'font-size: medium'}),
        }

    def save(self, payment=None, on_time=None):
        order = super().save(commit=False)
        if on_time is not None:
            order.order_time = on_time
            order.status_order = Order.ON_TIME
        if payment is not None:
            order.payment_method = payment
        order.save()
        return order


class SubscriberForm(ModelForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': _('Введіть пошту'),
        'style': 'font-size: medium',
        'id': 'sub_email'
    }),
        error_messages={'required': _('Введіть ел.пошту, будь ласка'),
                        'invalid': _('Введіть коректну ел.пошту')}
    )

    class Meta:
        model = SubscribeUsers
        fields = ('email',)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.email_validator(email) is None:
            raise forms.ValidationError(_("Невірний формат ел.пошти"))
        elif SubscribeUsers.get_by_email(email) is not None:
            raise forms.ValidationError(_("Ви вже підписались"))
        else:
            return email


class BonusForm(ModelForm):
    class Meta:
        model = Bonus
        fields = ('amount', 'description', 'category', 'vehicle')

        widgets = {
            'description': forms.TextInput(attrs={
                'id': 'bonus-description', 'placeholder': _('Опис'),
                'style': 'font-size: medium'}),
            'category': forms.Select(attrs={
                'id': 'bonus-category', 'name': "bonus-category", 'placeholder': _('Категорія'),
                'style': 'font-size: medium'}),
            'vehicle': forms.Select(attrs={
                'id': 'bonus-vehicle',
                'placeholder': _('Автомобіль'), 'style': 'font-size: medium'}),
        }

        labels = {
            'description': _('Опис'),
            'category': _('Категорія'),
            'vehicle': _('Автомобіль'),
        }

    amount = forms.DecimalField(widget=PhoneInput(attrs={'placeholder': _('Введіть суму')}),
                                label=_('Сума'),
                                required=True,
                                validators=[
                                    MinValueValidator(1, message=_('Сума повинна бути не менше 1')),
                                ],
                                error_messages={'required': _('Введіть суму, будь ласка'),
                                                'invalid': _('Сума повинна бути числом')}
                                )
    new_category = forms.CharField(
        required=False,
        label=_("Нова категорія"),
        widget=forms.TextInput(attrs={'id': 'new-category', 'style': 'font-size: medium',
                                      'placeholder': _('Введіть назву категорії')}),
        validators=[
            MinLengthValidator(5, message=_('Назва повинна мати не менше 5 символів')),
        ],
        error_messages={'required': _('Введіть суму, будь ласка'),
                        'invalid': _('Сума повинна бути числом')}
    )

    def __init__(self, user, category=None, payment_id=None, driver_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        filter_partner = user.manager.managers_partner if user.is_manager() else user
        if payment_id:
            payment = DriverPayments.objects.get(id=payment_id)
            driver_vehicle_ids = DriverReshuffle.objects.filter(
                Q(driver_start=payment.driver),
                Q(swap_time__range=(payment.report_from, payment.report_to)) |
                Q(end_time__range=(payment.report_from, payment.report_to))
            ).values_list('swap_vehicle', flat=True)
            self.fields['vehicle'].queryset = Vehicle.objects.filter(id__in=driver_vehicle_ids)
        else:
            payment = DriverPayments.objects.filter(driver=driver_id).last()
            
            driver_vehicle_ids = DriverReshuffle.objects.filter(
                Q(driver_start=driver_id),
                Q(swap_time__range=(payment.report_to, timezone.localtime())) |
                Q(end_time__range=(payment.report_to, timezone.localtime()))
            ).values_list('swap_vehicle', flat=True)
            self.fields['vehicle'].queryset = Vehicle.objects.filter(id__in=driver_vehicle_ids)
        filter_category = Q(bonuscategory__isnull=False) if category == 'bonus' else Q(bonuscategory__isnull=True)
        category_queryset = Category.objects.filter(Q(partner=filter_partner) |
                                                    Q(partner__isnull=True),
                                                    filter_category)
        category_choices = list(category_queryset.values_list('id', 'title'))
        category_choices.append(('add_new_category', _('Додати нову категорію')))
        self.fields['category'].choices = category_choices
        self.fields['description'].required = False
        self.fields['vehicle'].required = True
        if self.fields['vehicle'].queryset.count() == 1:
            self.fields['vehicle'].initial = self.fields['vehicle'].queryset.first()

    def is_valid(self):
        valid = super().is_valid()
        category = self.cleaned_data.get('category')
        new_category = self.cleaned_data.get('new_category')
        if not category and not new_category:
            self.add_error('new_category', _('Виберіть або введіть категорію'))
            del self.errors['category']
            valid = False
        if not category and new_category:
            del self.errors['category']
            if self.errors:
                valid = False
            else:
                valid = True
        return valid
