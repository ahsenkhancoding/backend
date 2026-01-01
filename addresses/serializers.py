# backend/addresses/serializers.py
from rest_framework import serializers
from .models import Address

class AddressSerializer(serializers.ModelSerializer):
    """
    Serializer for reading, creating, and updating user addresses.
    """
    # Make user read-only, it will be set automatically from the request context
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Address
        fields = [
            'id',
            'user',
            'address_line',
            'city',
            'pincode',
            'contact_name',
            'contact_phone',
            'is_default',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')

    def create(self, validated_data):
        """Assign the user from the request context during creation."""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    # The save method in the model handles the is_default logic automatically