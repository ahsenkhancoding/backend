# backend/cart/admin.py
from django.contrib import admin
from .models import Cart, CartItem

class CartItemInline(admin.TabularInline):
    model = CartItem
    fields = ('product', 'quantity', 'added_at')
    readonly_fields = ('product', 'added_at')
    extra = 0
    # Prevent editing items directly here for simplicity
    can_delete = False
    # Add autocomplete_fields if you have many products
    # autocomplete_fields = ['product']

    def has_add_permission(self, request, obj=None):
        return False # Don't add items via admin inline

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'updated_at', 'item_count')
    readonly_fields = ('id', 'user', 'created_at', 'updated_at')
    search_fields = ('user__phone_number', 'user__name')
    inlines = [CartItemInline]

    def item_count(self, obj):
        # Calculate total quantity of items in cart
        return sum(item.quantity for item in obj.items.all())
    item_count.short_description = 'Total Items'

# Optionally register CartItem separately for direct viewing/debugging
# @admin.register(CartItem)
# class CartItemAdmin(admin.ModelAdmin):
#    list_display = ('id', 'cart', 'product', 'quantity', 'added_at')
#    readonly_fields = ('id', 'cart', 'product', 'added_at')