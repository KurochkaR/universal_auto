from django.db.models import Q
from rest_framework import authentication

from app.models import SummaryReport, Driver, CarEfficiency, DriverEfficiency, Vehicle
from .permissions import IsPartnerUser, IsManagerUser, IsInvestorUser
from api.authentication import TokenAuthentication


class PartnerFilterMixin:
    def get_queryset(self, model):
        queryset = model.objects.filter(partner=self.request.user)
        return queryset


class ManagerFilterMixin:
    @staticmethod
    def get_queryset(model, user):

        model_filter_map = {
            SummaryReport: (Q(driver__in=Driver.objects.filter(manager=user)) | Q(partner=user)),
            CarEfficiency: (Q(vehicle__manager=user) | Q(partner=user)),
            DriverEfficiency: (Q(driver__manager=user) | Q(partner=user)),
            Vehicle: (Q(manager=user) | Q(partner=user)),
        }

        filter_condition = model_filter_map.get(model)
        if filter_condition:
            queryset = model.objects.filter(filter_condition)
        else:
            queryset = model.objects.none()

        return queryset


class InvestorFilterMixin:
    @staticmethod
    def get_queryset(model, user):
        if isinstance(model(), Vehicle):
            queryset = model.objects.filter(investor_car=user)
        elif isinstance(model(), CarEfficiency):
            queryset = model.objects.filter(vehicle__investor_car=user)
        else:
            queryset = model.objects.none()
        return queryset


class CombinedPermissionsMixin:
    authentication_classes = [authentication.SessionAuthentication,
                              TokenAuthentication]

    # def get_permissions(self):
    #     permissions = [
    #         IsManagerUser().has_permission(self.request, self),
    #         IsPartnerUser().has_permission(self.request, self),
    #         IsInvestorUser().has_permission(self.request, self),
    #     ]
    #
    #     for i, permission in enumerate(permissions):
    #         if permission:
    #             return [[IsManagerUser()], [IsPartnerUser()], [IsInvestorUser()]][i]
