# backend/shipping_delivery/models.py
from django.db import models
from django.core.validators import MinValueValidator

# Optional: Define upload path function for better organization
def delivery_option_logo_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/delivery_option_logos/{filename}
    # Consider adding instance.pk or a UUID for uniqueness if needed
    return f'delivery_option_logos/{filename}'

class DeliveryOption(models.Model):
    """
    Represents a delivery service/option available for orders.
    Managed via the Django Admin panel. Includes base charge and logo.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Name of the delivery option (e.g., TCS, Leopards Courier, Local Rider, Urgent Delivery)."
    )
    estimated_delivery_time = models.CharField(
        max_length=100,
        blank=True,
        help_text="Estimated delivery timeframe (e.g., '24-48 hours', 'Same Day'). Can be updated in Admin."
    )
    base_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0.00)],
        help_text="Base delivery charge for this option (PKR). Set to 0.00 for free delivery."
    )
    # <<< ADD Logo Field >>>
    logo = models.ImageField(
        upload_to=delivery_option_logo_path, # Store in 'media/delivery_option_logos/'
        null=True,          # Allow no logo
        blank=True,         # Allow empty in forms
        help_text="Upload the logo for this delivery service (optional)."
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Is this delivery option currently available for selection/use?"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} (Charge: {self.base_charge})"

    class Meta:
        verbose_name = "Delivery Option"
        verbose_name_plural = "Delivery Options"
        ordering = ['name']