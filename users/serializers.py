# backend/users/serializers.py
from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.core.validators import RegexValidator

# Get the custom user model defined in settings.AUTH_USER_MODEL
User = get_user_model()

# --- Keep UserRegistrationSerializer as is ---
class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration. Handles creation of new users based on CustomUser model.
    """
    password = serializers.CharField(
        write_only=True, required=True, style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True, required=True, style={'input_type': 'password'}
    )
    phone_number = serializers.CharField(
        required=True,
        validators=[
            RegexValidator(
                regex=r'^\+923\d{9}$', # e.g., +923xxxxxxxxx
                message="Phone number must be entered in the format: '+923xxxxxxxxx'."
            )
        ]
    )
    name = serializers.CharField(required=False, allow_blank=True, max_length=255)

    class Meta:
        model = User
        fields = ('phone_number', 'name', 'password', 'password_confirm')
        extra_kwargs = {'name': {'required': False}}

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Password fields didn't match."})
        if User.objects.filter(phone_number=attrs['phone_number']).exists():
             raise serializers.ValidationError({"phone_number": "This phone number is already registered."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user

# --- Ensure UserDetailSerializer is correct for GET/PATCH ---
class UserDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying and updating user details (excluding sensitive info).
    """
    class Meta:
        model = User
        # Fields relevant for user profile view/update
        fields = ('id', 'phone_number', 'name', 'is_active', 'date_joined')
        # Make phone number, ID, etc. read-only, but allow updating 'name'
        read_only_fields = ('id', 'phone_number', 'is_active', 'date_joined')

    # Optional: Add extra validation for update if needed
    # def validate_name(self, value):
    #     if len(value) < 2:
    #         raise serializers.ValidationError("Name must be at least 2 characters long.")
    #     return value