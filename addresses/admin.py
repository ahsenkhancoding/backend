# backend/addresses/admin.py
from django.contrib import admin
from .models import Address

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    """Admin configuration for the Address model."""
    list_display = (
        'user',
        'contact_name',
        'address_line',
        'city',
        'pincode',
        'contact_phone',
        'is_default',
        'updated_at',
    )
    list_filter = ('is_default', 'city', 'updated_at')
    search_fields = ('user__phone_number', 'user__name', 'contact_name', 'address_line', 'city', 'pincode', 'contact_phone')
    # Allow editing most fields, but user is set automatically via API
    readonly_fields = ('id', 'created_at', 'updated_at')
    # Group fields for better readability
    fieldsets = (
        (None, {'fields': ('user',)}), # Display user but usually read-only here
        ('Address Details', {'fields': ('address_line', 'city', 'pincode')}),
        ('Contact Information', {'fields': ('contact_name', 'contact_phone')}),
        ('Settings', {'fields': ('is_default',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )

    # Ensure only superusers or staff with specific permissions can edit addresses not their own
    # For simplicity now, admin has full access. Refine with get_queryset if needed.