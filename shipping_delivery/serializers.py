# backend/shipping_delivery/serializers.py
from rest_framework import serializers
from .models import DeliveryOption

class DeliveryOptionSerializer(serializers.ModelSerializer):
    """
    Serializer for DeliveryOption, including base charge and logo URL.
    """
    # <<< ADD Logo Field to Serializer >>>
    # ImageField automatically generates the full URL if context is available
    logo = serializers.ImageField(read_only=True)

    class Meta:
        model = DeliveryOption
        fields = [
            'id',
            'name',
            'estimated_delivery_time',
            'base_charge',
            'logo' # <<< ADD logo field
        ]
        