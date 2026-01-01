# backend/orders/serializers.py
from rest_framework import serializers
from django.db import transaction
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from decimal import Decimal # Import Decimal

from products.models import Product
from addresses.models import Address
from .models import Order, OrderItem
from .otp_service import send_order_otp, OTP_LENGTH
from shipping_delivery.models import DeliveryOption # Corrected import path
from shipping_delivery.serializers import DeliveryOptionSerializer # Corrected import path

User = get_user_model()

# --- OrderItemCreateSerializer (Keep As Is) ---
class OrderItemCreateSerializer(serializers.Serializer):
    sku = serializers.CharField(max_length=100, required=True)
    quantity = serializers.IntegerField(min_value=1, required=True)

# --- OrderCreateSerializer (MODIFIED) ---
class OrderCreateSerializer(serializers.Serializer):
    # Input Fields
    address_id = serializers.UUIDField(required=False, write_only=True, allow_null=True)
    shipping_name = serializers.CharField(max_length=255, required=False, write_only=True)
    shipping_phone_number = serializers.CharField(max_length=20, required=False, write_only=True)
    shipping_address_line = serializers.CharField(required=False, write_only=True)
    shipping_city = serializers.CharField(max_length=100, required=False, write_only=True)
    shipping_pincode = serializers.CharField(max_length=10, required=False, allow_blank=True, write_only=True)
    payment_method = serializers.CharField(max_length=50, default='COD', required=False, write_only=True)
    items = OrderItemCreateSerializer(many=True, required=True, write_only=True)
    prescription_upload = serializers.FileField(required=False, write_only=True, allow_null=True)
    delivery_option_id = serializers.IntegerField(required=False, write_only=True, allow_null=True) # <<< ADD Delivery Option ID input

    # Internal flags/data
    _requires_prescription = False
    _validated_address_instance = None
    _validated_delivery_option = None # To store fetched delivery option

    def validate_items(self, items_data):
        # Keep existing item validation logic...
        if not items_data: raise serializers.ValidationError("Order must contain at least one item.")
        self._requires_prescription = False; skus = [i['sku'] for i in items_data]
        products = Product.objects.filter(sku__in=skus).values('id','sku','selling_price','name','is_available','requires_prescription')
        sku_map = {p['sku']:p for p in products}; validated = []
        for item in items_data:
            info = sku_map.get(item['sku'])
            if not info: raise serializers.ValidationError(f"Product SKU '{item['sku']}' not found.")
            if not info['is_available']: raise serializers.ValidationError(f"Product '{info['name']}' unavailable.")
            if info['requires_prescription']: self._requires_prescription = True
            # Ensure price is Decimal
            price = Decimal(info['selling_price'] or 0)
            validated.append({'sku':item['sku'], 'quantity':item['quantity'], 'product_id':info['id'], 'price_per_item':price, 'product_name_snapshot':info['name']})
        if not validated: raise serializers.ValidationError("No valid items found.")
        return validated

    def validate_delivery_option_id(self, value):
        """Validate the provided delivery_option_id."""
        if value is None:
            return None # No option selected
        try:
            # Fetch and store the validated option instance
            option = DeliveryOption.objects.get(pk=value, is_active=True)
            self._validated_delivery_option = option
            return value
        except DeliveryOption.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive Delivery Option ID.")

    def validate(self, attrs):
        # Keep existing address validation logic...
        address_id = attrs.get('address_id'); shipping_provided = all(attrs.get(f) for f in ['shipping_name','shipping_phone_number','shipping_address_line','shipping_city'])
        user = self.context['request'].user
        if address_id and shipping_provided: raise serializers.ValidationError("Provide address_id or shipping details, not both.")
        if not address_id and not shipping_provided: raise serializers.ValidationError("Address ID or full shipping details required.")
        if address_id:
            try: self._validated_address_instance = Address.objects.get(pk=address_id, user=user)
            except Address.DoesNotExist: raise serializers.ValidationError({"address_id": "Invalid address ID or address does not belong to user."})
        # Keep existing prescription validation...
        if self._requires_prescription and not attrs.get('prescription_upload'): raise serializers.ValidationError({"prescription_upload": "Prescription file required."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user = self.context['request'].user
        items_data = validated_data.pop('items')
        prescription_file = validated_data.pop('prescription_upload', None)
        # address = validated_data.pop('_validated_address_instance', None) # Use internal flag
        address = self._validated_address_instance # Use stored instance
        delivery_option = self._validated_delivery_option # Use stored instance

        # Calculate sub_total from items
        sub_total = sum(item['price_per_item'] * item['quantity'] for item in items_data)

        # Determine delivery charge
        delivery_charge = Decimal('0.00')
        if delivery_option:
            delivery_charge = delivery_option.base_charge

        # Calculate final order total
        order_total = sub_total + delivery_charge

        # Prepare shipping details
        shipping = {}
        if address: shipping = {'shipping_name': address.contact_name, 'shipping_phone_number': address.contact_phone, 'shipping_address_line': address.address_line, 'shipping_city': address.city, 'shipping_pincode': address.pincode}
        else: shipping = {k:validated_data.get(k) for k in ['shipping_name','shipping_phone_number','shipping_address_line','shipping_city','shipping_pincode']}

        # Determine prescription status
        rx_status = Order.PrescriptionStatus.PENDING_VERIFICATION if self._requires_prescription and prescription_file else (Order.PrescriptionStatus.PENDING_UPLOAD if self._requires_prescription else Order.PrescriptionStatus.NOT_REQUIRED)
        order_status = Order.OrderStatus.PENDING # Start as PENDING before OTP

        # Create the Order instance
        order = Order.objects.create(
            user=user,
            sub_total=sub_total, # Save sub total
            delivery_charge_snapshot=delivery_charge, # Save delivery charge snapshot
            order_total=order_total, # Save calculated total
            delivery_option=delivery_option, # Link to selected option (can be None)
            order_requires_prescription=self._requires_prescription,
            prescription_status=rx_status,
            status=order_status,
            payment_method=validated_data.get('payment_method','COD'),
            **shipping # Unpack shipping details
        )

        # Assign prescription if uploaded
        if prescription_file:
            order.prescription = prescription_file
            order.save(update_fields=['prescription'])

        # Create order items
        items = [OrderItem(order=order, product_id=i['product_id'], price_per_item=i['price_per_item'], quantity=i['quantity'], product_name_snapshot=i['product_name_snapshot'], product_sku_snapshot=i['sku']) for i in items_data]
        if items: OrderItem.objects.bulk_create(items)

        # Send OTP
        otp_sent = send_order_otp(order) # Trigger OTP send
        if not otp_sent:
             raise serializers.ValidationError("Failed to send order confirmation OTP. Please check order status or contact support.") # Consider logging instead

        return order

# --- OrderOtpVerifySerializer (Keep As Is) ---
class OrderOtpVerifySerializer(serializers.Serializer):
    otp_code = serializers.CharField(max_length=OTP_LENGTH, min_length=OTP_LENGTH, required=True, write_only=True)
    def validate_otp_code(self, value):
        if not value.isdigit(): raise serializers.ValidationError("OTP must be numeric.")
        return value

# --- OrderItemSerializer (Keep As Is) ---
class OrderItemSerializer(serializers.ModelSerializer):
    item_total = serializers.DecimalField(max_digits=12, decimal_places=2, source='get_item_total', read_only=True)
    product_sku_snapshot = serializers.CharField(read_only=True)
    class Meta: model = OrderItem; fields = ['id','product','product_name_snapshot','product_sku_snapshot','price_per_item','quantity','item_total']; read_only_fields = fields

# --- OrderSerializer (MODIFIED) ---
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user = serializers.StringRelatedField(read_only=True)
    status = serializers.CharField(source='get_status_display', read_only=True)
    prescription_status = serializers.CharField(source='get_prescription_status_display', read_only=True)
    prescription_url = serializers.SerializerMethodField(read_only=True)
    is_otp_verified = serializers.BooleanField(read_only=True)
    order_number = serializers.CharField(read_only=True)
    delivery_option = DeliveryOptionSerializer(read_only=True) # Keep this

    # <<< ADD sub_total and delivery_charge_snapshot >>>
    sub_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    delivery_charge_snapshot = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'user', 'status',
            'sub_total', # <<< Add sub_total
            'delivery_charge_snapshot', # <<< Add delivery_charge_snapshot
            'order_total', # Keep overall total
            'shipping_name', 'shipping_phone_number', 'shipping_address_line', 'shipping_city', 'shipping_pincode',
            'payment_method', 'payment_completed',
            'delivery_option', # Keep nested delivery option details
            'tracking_number',
            'created_at', 'updated_at',
            'order_requires_prescription', 'prescription_status', 'prescription_url',
            'is_otp_verified',
            'items'
        ]
        read_only_fields = fields

    def get_prescription_url(self, obj):
        request = self.context.get('request')
        if obj.prescription and hasattr(obj.prescription, 'url'):
            if request: return request.build_absolute_uri(obj.prescription.url)
            return obj.prescription.url
        return None