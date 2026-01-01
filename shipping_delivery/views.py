# backend/shipping_delivery/views.py
from rest_framework import viewsets, permissions
from .models import DeliveryOption
from .serializers import DeliveryOptionSerializer

class DeliveryOptionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DeliveryOption.objects.filter(is_active=True).order_by('name')
    serializer_class = DeliveryOptionSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None
    