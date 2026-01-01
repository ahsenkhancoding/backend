# backend/cart/models.py
from django.db import models
from django.conf import settings # To link to CustomUser
from django.core.validators import MinValueValidator
import uuid
from products.models import Product # Link to Product model

class Cart(models.Model):
    """
    Represents a shopping cart, associated with a user.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Link to the user. Each user should ideally have only one active cart.
    # Using OneToOneField ensures this. If user is deleted, cart can be deleted too.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart for {self.user.phone_number}"

    # Consider adding methods to calculate total price, item count etc. later if needed
    # def get_total_price(self): ...
    # def get_total_items(self): ...

    class Meta:
        verbose_name = "Shopping Cart"
        verbose_name_plural = "Shopping Carts"


class CartItem(models.Model):
    """
    Represents an item within a shopping cart.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Link back to the Cart it belongs to. Deleting cart deletes items.
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    # Link to the actual Product. If Product is deleted, maybe set item's product to NULL?
    # Or handle deletion more explicitly. For now, SET_NULL is okay.
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, related_name='cart_items')
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)] # Ensure quantity is at least 1
    )
    # Store price at the time it was added? Optional, often cart uses current price.
    # added_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"
        # Ensure a user cannot have the same product twice in their cart; use unique_together
        unique_together = ('cart', 'product')
        ordering = ['added_at'] # Show items in the order they were added

    def __str__(self):
        prod_name = self.product.name if self.product else "Product Removed"
        return f"{self.quantity} x {prod_name} in {self.cart}"

    # Consider adding method to get item subtotal later
    # def get_item_subtotal(self): ...