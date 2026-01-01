# backend/cart/views.py
from rest_framework import viewsets, status, mixins, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
# Make sure MultiPartParser, FormParser are imported if needed elsewhere, but not strictly needed for CartViewSet
# from rest_framework.parsers import MultiPartParser, FormParser

from .models import Cart, CartItem
from .serializers import (
    CartSerializer, CartItemSerializer, AddCartItemSerializer, UpdateCartItemSerializer
)

# --- UPDATE CartViewSet Inheritance and add list method ---
class CartViewSet(
    mixins.ListModelMixin,     # ADDED: To handle GET /cart/
    mixins.RetrieveModelMixin, # Handles GET /cart/{pk}/ (though we override get_object)
    mixins.DestroyModelMixin,  # Handles DELETE /cart/
    viewsets.GenericViewSet
):
    """
    API endpoint for viewing, clearing, and managing items in the user's cart.
    GET /cart/ retrieves the user's cart.
    DELETE /cart/ clears the user's cart items.
    POST /cart/items/ adds an item.
    PATCH /cart/items/{item_pk}/ updates item quantity.
    DELETE /cart/items/{item_pk}/ removes an item.
    """
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Ensure we only deal with the authenticated user's cart."""
        user = self.request.user
        # Prefetch items and related products for efficiency
        return Cart.objects.filter(user=user).prefetch_related('items__product')

    def get_object(self):
        """Retrieve or create the cart for the authenticated user."""
        queryset = self.get_queryset()
        cart, created = queryset.get_or_create(user=self.request.user)
        return cart

    # --- Override list action to behave like retrieve for the single user cart ---
    def list(self, request, *args, **kwargs):
        """Maps GET /cart/ to retrieve the user's single cart."""
        return self.retrieve(request, *args, **kwargs)
    # --------------------------------------------------------------------------

    # --- retrieve method uses get_object, so it works for the user's cart ---
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    # --- Overriding destroy to clear items ---
    def perform_destroy(self, instance: Cart):
        """Clear all items from the cart."""
        instance.items.all().delete()

    def destroy(self, request, *args, **kwargs):
        """Endpoint to clear the cart (DELETE /cart/)."""
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


    # --- Keep Actions for Managing Cart Items ---
    @action(detail=False, methods=['post'], serializer_class=AddCartItemSerializer, url_path='items')
    def add_item(self, request):
        """Add an item to the cart (POST /cart/items/)."""
        cart = self.get_object()
        serializer = self.get_serializer(data=request.data, context={'cart': cart, 'request': request}) # Pass request to context
        serializer.is_valid(raise_exception=True)
        serializer.save()
        cart_serializer = CartSerializer(cart, context={'request': request}) # Pass request to context for nested serializers if needed
        return Response(cart_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['patch'], serializer_class=UpdateCartItemSerializer, url_path='items/(?P<item_pk>[^/.]+)')
    def update_item(self, request, item_pk=None):
        """Update quantity of a specific item in the cart (PATCH /cart/items/{item_pk}/)."""
        cart = self.get_object()
        cart_item = get_object_or_404(CartItem, pk=item_pk, cart=cart)
        serializer = self.get_serializer(cart_item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        cart_serializer = CartSerializer(cart, context={'request': request})
        return Response(cart_serializer.data)

    @action(detail=False, methods=['delete'], url_path='items/(?P<item_pk>[^/.]+)')
    def remove_item(self, request, item_pk=None):
        """Remove a specific item from the cart (DELETE /cart/items/{item_pk}/)."""
        cart = self.get_object()
        cart_item = get_object_or_404(CartItem, pk=item_pk, cart=cart)
        cart_item.delete()
        cart_serializer = CartSerializer(cart, context={'request': request})
        return Response(cart_serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['delete'], url_path='items/(?P<item_pk>[^/.]+)')
    def remove_item(self, request, item_pk=None):
        """Remove a specific item from the cart (DELETE /cart/items/{item_id}/)."""
        cart = self.get_object()
        cart_item = get_object_or_404(CartItem, pk=item_pk, cart=cart)
        cart_item.delete()
        # Return the updated cart view
        cart_serializer = CartSerializer(cart, context={'request': request})
        return Response(cart_serializer.data, status=status.HTTP_200_OK) # Or 204 if preferred