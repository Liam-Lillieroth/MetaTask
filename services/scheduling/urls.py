from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SchedulableResourceViewSet,
    BookingRequestViewSet,
    ResourceScheduleRuleViewSet,
    IntegrationViewSet
)

app_name = 'scheduling'

router = DefaultRouter()
router.register(r'resources', SchedulableResourceViewSet, basename='resource')
router.register(r'bookings', BookingRequestViewSet, basename='booking')
router.register(r'rules', ResourceScheduleRuleViewSet, basename='rule')
router.register(r'integrations', IntegrationViewSet, basename='integration')

urlpatterns = [
    path('api/', include(router.urls)),
]