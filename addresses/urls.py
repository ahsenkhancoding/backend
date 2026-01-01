# backend/addresses/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AddressViewSet

app_name = 'addresses'

router = DefaultRouter()
# Register the AddressViewSet. URLs like /addresses/ and /addresses/{id}/ will be created.
router.register(r'addresses', AddressViewSet, basename='address')

urlpatterns = [
    path('', include(router.urls)),
]