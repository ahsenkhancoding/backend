# backend/users/views.py
from django.contrib.auth import get_user_model
from rest_framework import generics, permissions
from rest_framework.response import Response
# Import both serializers
from .serializers import UserRegistrationSerializer, UserDetailSerializer

User = get_user_model()

# --- Keep UserRegistrationView as is ---
class UserRegistrationView(generics.CreateAPIView):
    """
    API view for creating (registering) a new user.
    Allows POST requests for registration.
    """
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny] # Anyone can register
    serializer_class = UserRegistrationSerializer


# --- ADD View for retrieving/updating the currently logged-in user's profile ---
class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    API view for retrieving (GET) and updating (PATCH/PUT)
    the profile of the currently authenticated user.
    """
    queryset = User.objects.all() # Base queryset
    serializer_class = UserDetailSerializer
    permission_classes = [permissions.IsAuthenticated] # User must be logged in

    def get_object(self):
        """
        Override get_object to always return the request.user.
        This ensures users can only access/update their own profile.
        """
        return self.request.user

    # PUT requests require all fields, PATCH allows partial updates
    # RetrieveUpdateAPIView handles GET, PUT, PATCH automatically based on serializer