# backend/shipping_delivery/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DeliveryOptionViewSet

router = DefaultRouter()
# Keep URL path user-friendly
router.register(r'delivery-options', DeliveryOptionViewSet, basename='delivery-option')

urlpatterns = [
    path('', include(router.urls)),
]
