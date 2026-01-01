# backend/users/urls.py
from django.urls import path
# Import the new view
from .views import UserRegistrationView, UserProfileView
# Import views from simplejwt for token handling
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

app_name = 'users'

urlpatterns = [
    # Registration endpoint
    path('register/', UserRegistrationView.as_view(), name='register'),

    # Login endpoint
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    # Refresh token endpoint
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # --- ADD User Profile endpoint ---
    # GET retrieves profile, PUT/PATCH updates it
    path('profile/', UserProfileView.as_view(), name='profile'),
    # ---------------------------------
]