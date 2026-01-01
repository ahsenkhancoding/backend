# backend/orders/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
# Import the new view
from .views import OrderViewSet, OrderOtpVerifyView

app_name = 'orders'

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')

urlpatterns = [
    # Include the router-generated URLs (/orders/, /orders/{id}/)
    path('', include(router.urls)),

    # --- ADD specific path for OTP verification ---
    # Use order_id (which is the UUID primary key) in the URL
    path('orders/<uuid:order_id>/verify-otp/', OrderOtpVerifyView.as_view(), name='order-verify-otp'),
    # ---------------------------------------------
]
