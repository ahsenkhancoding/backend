# backend/shipping_delivery/admin.py
from django.contrib import admin
from django.utils.html import format_html # Import format_html
from .models import DeliveryOption

@admin.register(DeliveryOption)
class DeliveryOptionAdmin(admin.ModelAdmin):
    """
    Admin interface for managing Delivery Options.
    Allows editing name, estimated time, active status, base charge, and logo.
    """
    list_display = (
        'name',
        'logo_preview', # <<< ADD logo preview method name
        'estimated_delivery_time',
        'base_charge',
        'is_active',
        'updated_at'
    )
    list_filter = ('is_active',)
    search_fields = ('name',)
    list_editable = (
        'estimated_delivery_time',
        'base_charge',
        'is_active'
    )
    readonly_fields = (
        'created_at',
        'updated_at',
        'logo_preview_detail' # <<< Add method name for detail view preview
        )
    fieldsets = (
        (None, {
            'fields': ('name', 'is_active')
        }),
        ('Logo', { # <<< ADD Logo section
             'fields': ('logo', 'logo_preview_detail') # Add logo upload field and preview
        }),
        ('Delivery Details', {
            'fields': (
                'estimated_delivery_time',
                'base_charge'
                )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    # <<< ADD Method for list view logo preview >>>
    def logo_preview(self, obj):
        if obj.logo:
            # Limit image size in the list view
            return format_html('<img src="{}" style="max-height: 40px; max-width: 100px;" />', obj.logo.url)
        return "(No logo)"
    logo_preview.short_description = 'Logo Preview'

    # <<< ADD Method for detail view logo preview >>>
    def logo_preview_detail(self, obj):
        if obj.logo:
             # Larger preview for detail view
            return format_html('<img src="{}" style="max-height: 150px; max-width: 200px;" />', obj.logo.url)
        return "(No logo uploaded)"
    logo_preview_detail.short_description = 'Current Logo'