# backend/orders/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid
import random
from datetime import timedelta
from django.core.validators import MinValueValidator # Import validator for charge

from products.models import Product
from shipping_delivery.models import DeliveryOption # Corrected import path

# --- prescription_upload_path function (Keep As Is) ---
def prescription_upload_path(instance, filename):
    order_ident = instance.order_number or instance.id or f"unsaved_{timezone.now().strftime('%Y%m%d%H%M%S')}"
    return f'prescriptions/order_{order_ident}/{filename}'

class Order(models.Model):
    # --- Enums (OrderStatus, PrescriptionStatus) (Keep As Is) ---
    class OrderStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'; AWAITING_OTP_VERIFICATION = 'AWAITING_OTP', 'Awaiting OTP Verification'; AWAITING_PRESCRIPTION = 'AWAITING_RX', 'Awaiting Prescription'; PROCESSING = 'PROCESSING', 'Processing'; SOURCING = 'SOURCING', 'Sourcing'; SHIPPED = 'SHIPPED', 'Shipped'; DELIVERED = 'DELIVERED', 'Delivered'; CANCELLED = 'CANCELLED', 'Cancelled'; REFUNDED = 'REFUNDED', 'Refunded'
    class PrescriptionStatus(models.TextChoices):
        NOT_REQUIRED = 'NA', 'Not Required'; PENDING_UPLOAD = 'PENDING_UPLOAD', 'Pending Upload'; PENDING_VERIFICATION = 'PENDING_VERIFICATION', 'Pending Verification'; VERIFIED = 'VERIFIED', 'Verified'; REJECTED = 'REJECTED', 'Rejected'

    # --- Base Fields (Keep As Is) ---
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True, blank=True, null=True, editable=False, db_index=True, verbose_name="Order Number")

    # --- Shipping Details (Keep As Is) ---
    shipping_name = models.CharField(max_length=255); shipping_phone_number = models.CharField(max_length=20); shipping_address_line = models.TextField(); shipping_city = models.CharField(max_length=100); shipping_pincode = models.CharField(max_length=10, blank=True, null=True)

    # --- Order Details ---
    sub_total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="Total price of items before delivery charge.") # <<< ADD Sub Total
    delivery_charge_snapshot = models.DecimalField( # <<< ADD Delivery Charge Snapshot
        max_digits=10, decimal_places=2, default=0.00,
        validators=[MinValueValidator(0.00)],
        help_text="Delivery charge applied at the time of order creation."
    )
    order_total = models.DecimalField(max_digits=12, decimal_places=2, help_text="Total amount including items and delivery charge.") # Keep order_total
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING, db_index=True)
    order_requires_prescription = models.BooleanField(default=False, editable=False, help_text="Indicates if any item in the order requires a prescription.")

    # --- Prescription Fields (Keep As Is) ---
    prescription = models.FileField(upload_to=prescription_upload_path, null=True, blank=True, help_text="Upload prescription file if required (PDF, JPG, PNG).")
    prescription_status = models.CharField(max_length=25, choices=PrescriptionStatus.choices, default=PrescriptionStatus.NOT_REQUIRED, db_index=True, help_text="Verification status of the uploaded prescription.")

    # --- Payment Fields (Keep As Is) ---
    payment_method = models.CharField(max_length=50, default='COD')
    payment_completed = models.BooleanField(default=False)

    # --- Delivery & Tracking Fields (Keep As Is) ---
    delivery_option = models.ForeignKey(DeliveryOption, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name="Assigned Delivery Option")
    tracking_number = models.CharField(max_length=100, blank=True, null=True)

    # --- OTP Fields (Keep As Is) ---
    otp_code = models.CharField(max_length=6, blank=True, null=True, help_text="Generated OTP code for order confirmation."); otp_expiry = models.DateTimeField(blank=True, null=True, help_text="Time when the OTP code expires."); is_otp_verified = models.BooleanField(default=False, help_text="Indicates if the order confirmation OTP has been successfully verified.")

    # --- Timestamps (Keep As Is) ---
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    # --- Model Methods (Keep existing, ensure save override is correct) ---
    def is_otp_valid(self, submitted_otp):
        if not self.otp_code or not self.otp_expiry: return False
        if not submitted_otp or len(submitted_otp) != len(self.otp_code): return False
        if timezone.now() > self.otp_expiry: return False
        return self.otp_code == submitted_otp

    def save(self, *args, **kwargs):
        # Generate order number only on creation
        if not self.order_number and not self.pk:
            today_str = timezone.now().strftime('%y%m%d')
            today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            last_order = Order.objects.filter(created_at__gte=today_start, created_at__lt=today_end, order_number__startswith=today_str).order_by('-order_number').first()
            next_seq = 1
            if last_order and last_order.order_number:
                try: last_seq_str = last_order.order_number.split('-')[-1]; next_seq = int(last_seq_str) + 1
                except (IndexError, ValueError, TypeError): pass
            self.order_number = f"{today_str}-{next_seq:04d}"

        # Recalculate total if sub_total or delivery_charge changes (optional, usually set on create)
        # self.order_total = (self.sub_total or 0) + (self.delivery_charge_snapshot or 0)

        super().save(*args, **kwargs)

    def __str__(self):
        display_id = self.order_number if self.order_number else f"UUID {self.id}"
        user_display = f" by {self.user.phone_number}" if self.user else ""
        return f"Order {display_id}{user_display} - Status: {self.get_status_display()}"

    class Meta:
        ordering = ['-created_at']

# --- OrderItem Model (Keep As Is) ---
class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, related_name='order_items')
    price_per_item = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    product_name_snapshot = models.CharField(max_length=255, blank=True)
    product_sku_snapshot = models.CharField(max_length=100, blank=True, null=True)
    def get_item_total(self): return (self.price_per_item or 0) * (self.quantity or 0)
    def save(self, *args, **kwargs):
        if self.product and not self.product_name_snapshot: self.product_name_snapshot = self.product.name
        if self.product and not self.product_sku_snapshot: self.product_sku_snapshot = self.product.sku
        super().save(*args, **kwargs)
    def __str__(self):
        prod_name = self.product_name_snapshot or (self.product.name if self.product else 'N/A')
        order_display = self.order.order_number if hasattr(self.order, 'order_number') and self.order.order_number else self.order.id
        return f"{self.quantity} x {prod_name} in Order {order_display}"