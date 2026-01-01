# backend/cart/serializers.py
from rest_framework import serializers
from django.shortcuts import get_object_or_404
from django.conf import settings

from .models import Cart, CartItem
from products.models import Product
# Import ProductSerializer to show product details within cart item
from products.serializers import ProductSerializer

User = settings.AUTH_USER_MODEL

class CartItemSerializer(serializers.ModelSerializer):
    """Serializer for displaying items within a cart."""
    # Use ProductSerializer for nested product details
    product = ProductSerializer(read_only=True)
    # Calculated subtotal for the item (quantity * current product price)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'quantity', 'subtotal', 'added_at']
        read_only_fields = ['id', 'product', 'subtotal', 'added_at'] # Quantity can be updated

    def get_subtotal(self, cart_item: CartItem):
        """Calculate subtotal based on current product price."""
        if cart_item.product:
            return cart_item.quantity * cart_item.product.selling_price
        return 0


class CartSerializer(serializers.ModelSerializer):
    """Serializer for displaying the user's cart."""
    # Use CartItemSerializer for nested items
    items = CartItemSerializer(many=True, read_only=True)
    # Calculated total price for the cart
    total_price = serializers.SerializerMethodField()
    # Total number of items (sum of quantities)
    total_items = serializers.SerializerMethodField()
    # Display user info simply
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'total_price', 'total_items', 'updated_at']
        read_only_fields = fields # Cart details are generally read-only via this serializer

    def get_total_price(self, cart: Cart):
        """Calculate total price by summing item subtotals."""
        total = 0
        # Access prefetched items if available (optimized in view)
        items = cart.items.all() if hasattr(cart, 'items') else CartItem.objects.filter(cart=cart)
        for item in items.select_related('product'): # Ensure product is selected
            if item.product:
                total += item.quantity * item.product.selling_price
        return total

    def get_total_items(self, cart: Cart):
        """Calculate total number of items (sum of quantities)."""
        # Access prefetched items if available
        items = cart.items.all() if hasattr(cart, 'items') else CartItem.objects.filter(cart=cart)
        return sum(item.quantity for item in items)


class AddCartItemSerializer(serializers.Serializer):
    """Serializer for adding an item to the cart."""
    product_id = serializers.IntegerField() # Use product ID instead of SKU for simplicity here
    quantity = serializers.IntegerField(min_value=1, default=1)

    def validate_product_id(self, value):
        """Check if the product exists and is available."""
        try:
            product = Product.objects.get(pk=value, is_available=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found or is unavailable.")
        return value # Return the validated product ID

    def save(self, **kwargs):
        """Adds item to cart or updates quantity if it already exists."""
        cart = self.context['cart'] # Get cart from context provided by view
        product_id = self.validated_data['product_id']
        quantity = self.validated_data['quantity']

        try:
            # Try to get existing item
            cart_item = CartItem.objects.get(cart=cart, product_id=product_id)
            # Update quantity if item exists
            cart_item.quantity += quantity
            # Optional: Add validation for max quantity per item if needed
            cart_item.save()
            self.instance = cart_item # Set instance for potential response serialization
        except CartItem.DoesNotExist:
            # Create new item if it doesn't exist
            self.instance = CartItem.objects.create(cart=cart, product_id=product_id, quantity=quantity)

        return self.instance


class UpdateCartItemSerializer(serializers.ModelSerializer):
    """Serializer for updating the quantity of an item in the cart."""
    # Only allow updating the quantity
    class Meta:
        model = CartItem
        fields = ['quantity']
        extra_kwargs = {
            'quantity': {'min_value': 1} # Ensure quantity remains positive
        }