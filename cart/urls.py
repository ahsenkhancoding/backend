# backend/cart/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CartViewSet

app_name = 'cart'

# Use a router to automatically generate URLs for the CartViewSet
# It will create URLs like: /cart/ (GET, DELETE), /cart/items/ (POST), etc.
router = DefaultRouter()
# Register CartViewSet with base name 'cart'. The lookup is handled internally by get_object.
# We don't register with a lookup like pk because we always operate on the user's single cart.
router.register(r'cart', CartViewSet, basename='cart')

urlpatterns = [
    # Include the router-generated URLs
    path('', include(router.urls)),
]
