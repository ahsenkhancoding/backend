# backend/addresses/views.py
from rest_framework import viewsets, permissions
from .models import Address
from .serializers import AddressSerializer

class AddressViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to view, create, edit, and delete their own addresses.
    Provides full CRUD operations filtered by the authenticated user.
    """
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated] # User must be logged in

    def get_queryset(self):
        """
        This view should return a list of all addresses
        for the currently authenticated user.
        """
        user = self.request.user
        if user.is_authenticated:
            return Address.objects.filter(user=user).order_by('-is_default', '-updated_at')
        return Address.objects.none() # Should not happen due to permission class

    def perform_create(self, serializer):
        """Ensure the address is saved with the correct user."""
        # The serializer's create method now handles assigning the user
        serializer.save()

    # ModelViewSet provides standard create, retrieve, update, partial_update, destroy, list actions
    # Filtering by user is handled in get_queryset
    