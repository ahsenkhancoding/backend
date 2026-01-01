# backend/addresses/models.py
from django.db import models
from django.conf import settings # To link to CustomUser
import uuid
from django.utils.translation import gettext_lazy as _

class Address(models.Model):
    """
    Represents a saved shipping address for a user.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Link to the user who owns this address. Delete addresses if user is deleted.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='addresses'
    )
    # Address details
    address_line = models.TextField(verbose_name=_("Address Line"))
    city = models.CharField(max_length=100, verbose_name=_("City"))
    pincode = models.CharField(max_length=10, verbose_name=_("Pincode"), blank=True, null=True)
    # You might add state/province if needed for your context
    # state = models.CharField(max_length=100, verbose_name=_("State/Province"), blank=True)

    # Contact details associated with this specific address (can differ from user's main contact)
    contact_name = models.CharField(max_length=255, verbose_name=_("Contact Name"), help_text=_("Name of the person at this address"))
    contact_phone = models.CharField(max_length=20, verbose_name=_("Contact Phone"), help_text=_("Phone number for delivery contact"))

    # Optional: Allow user to mark a default address
    is_default = models.BooleanField(default=False, verbose_name=_("Default Address"))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Address")
        verbose_name_plural = _("Addresses")
        ordering = ['-is_default', '-updated_at'] # Show default first, then newest

    def __str__(self):
        return f"{self.contact_name}, {self.address_line}, {self.city} - User: {self.user.phone_number}"

    def save(self, *args, **kwargs):
        """ Ensure only one address can be default per user """
        if self.is_default:
            # Set all other addresses for this user to non-default
            Address.objects.filter(user=self.user).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)