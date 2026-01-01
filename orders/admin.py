# backend/orders/admin.py
from django.contrib import admin, messages
from django.utils.html import format_html
from django.urls import reverse
from .models import Order, OrderItem

# --- OrderItemInline (Keep As Is) ---
class OrderItemInline(admin.TabularInline):
    model = OrderItem; fields = ('product_link', 'product_name_snapshot', 'product_sku_snapshot', 'price_per_item', 'quantity', 'get_item_total'); readonly_fields = ('product_link', 'product_name_snapshot', 'product_sku_snapshot', 'get_item_total'); extra = 0; can_delete = False
    def get_item_total(self, obj): return obj.get_item_total(); get_item_total.short_description = 'Item Total'
    def product_link(self, obj):
        if obj.product: link = reverse("admin:products_product_change", args=[obj.product.id]); return format_html('<a href="{}">{}</a>', link, obj.product_sku_snapshot or obj.product.sku or "View Product")
        return "N/A"
    product_link.short_description = 'Product SKU'
    def has_add_permission(self, request, obj=None): return False

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number', 'user_display', 'status', 'delivery_option',
        'sub_total', # <<< ADD
        'delivery_charge_snapshot', # <<< ADD
        'order_total', # Keep overall total
        'is_otp_verified', 'prescription_status_display', 'payment_method', 'shipping_city', 'created_at',
    )
    list_filter = ('status', 'is_otp_verified', 'prescription_status', 'payment_completed', 'payment_method', 'created_at', 'shipping_city', 'delivery_option')
    search_fields = ('order_number', 'id__iexact', 'user__phone_number', 'user__name', 'shipping_name', 'shipping_phone_number', 'tracking_number')
    readonly_fields = (
        'order_number', 'id', 'user',
        'sub_total', # <<< ADD
        'delivery_charge_snapshot', # <<< ADD
        'order_total', # Keep overall total read-only
        'created_at', 'updated_at', 'order_requires_prescription', 'prescription_display', 'otp_code', 'otp_expiry', 'is_otp_verified'
    )
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Order Information', {
            'fields': (
                'order_number', 'id', 'user', 'status',
                'sub_total', # <<< ADD
                'delivery_charge_snapshot', # <<< ADD
                'order_total', # Keep overall total
                'created_at', 'updated_at', 'order_requires_prescription'
            )
        }),
        ('OTP Verification', {'fields': ('is_otp_verified', 'otp_code', 'otp_expiry'), 'classes': ('collapse',)}),
        ('Prescription Details', {'fields': ('prescription_status', 'prescription', 'prescription_display')}),
        ('Shipping Details', {'fields': ('shipping_name', 'shipping_phone_number', 'shipping_address_line', 'shipping_city', 'shipping_pincode')}),
        ('Payment & Delivery', {'fields': ('payment_method', 'payment_completed', 'delivery_option', 'tracking_number')}),
    )
    inlines = [OrderItemInline]
    actions = ['mark_otp_verified_admin', 'mark_processing', 'mark_shipped', 'mark_delivered', 'mark_prescription_verified', 'mark_prescription_rejected', 'mark_awaiting_prescription']

    # --- Keep all action methods and display methods as they were ---
    @admin.action(description='Admin: Mark selected orders as OTP Verified') # ... etc ...
    def mark_otp_verified_admin(self, request, queryset): pass # Replace with your actual method code
    @admin.action(description='Mark selected orders as Processing') # ... etc ...
    def mark_processing(self, request, queryset): pass # Replace with your actual method code
    @admin.action(description='Mark selected orders as Shipped') # ... etc ...
    def mark_shipped(self, request, queryset): pass # Replace with your actual method code
    @admin.action(description='Mark selected orders as Delivered') # ... etc ...
    def mark_delivered(self, request, queryset): pass # Replace with your actual method code
    @admin.action(description='Verify selected prescriptions') # ... etc ...
    def mark_prescription_verified(self, request, queryset): pass # Replace with your actual method code
    @admin.action(description='Reject selected prescriptions') # ... etc ...
    def mark_prescription_rejected(self, request, queryset): pass # Replace with your actual method code
    @admin.action(description='Mark selected orders as Awaiting Prescription Upload') # ... etc ...
    def mark_awaiting_prescription(self, request, queryset): pass # Replace with your actual method code
    def user_display(self, obj): pass # Replace with your actual method code
    def prescription_status_display(self, obj): pass # Replace with your actual method code
    def prescription_display(self, obj): pass # Replace with your actual method code