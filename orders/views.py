# backend/orders/views.py

from rest_framework import generics, permissions, status, viewsets, mixins
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.views import APIView

# Import the serializers and models
from .serializers import (
    OrderCreateSerializer, OrderSerializer, OrderOtpVerifySerializer
)
from .models import Order, OrderItem

# --- Modified OrderViewSet ---
class OrderViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.action == 'create': return OrderCreateSerializer
        # Retrieve/List actions will use OrderSerializer
        return OrderSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated: return Order.objects.filter(user=user).prefetch_related('items__product').order_by('-created_at')
        return Order.objects.none()

    def perform_create(self, serializer):
        # This correctly saves the order using OrderCreateSerializer's logic
        serializer.save(user=self.request.user)

    # --- !!! ADD THIS METHOD OVERRIDE !!! ---
    def create(self, request, *args, **kwargs):
        """
        Override the default create method to use OrderSerializer for the response.
        """
        # Use the designated serializer for input validation and saving
        create_serializer = self.get_serializer(data=request.data)
        create_serializer.is_valid(raise_exception=True)
        # perform_create saves the instance using the create_serializer logic
        self.perform_create(create_serializer)

        # Now, create the response using the standard OrderSerializer
        # create_serializer.instance holds the newly created order object
        response_serializer = OrderSerializer(create_serializer.instance, context=self.get_serializer_context())

        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    # --- End of added method override ---


# --- Keep OrderOtpVerifyView exactly as you had it ---
class OrderOtpVerifyView(APIView):
    """
    API view to verify the OTP for a specific order.
    Handles POST requests to /api/orders/{order_id}/verify-otp/
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OrderOtpVerifySerializer # For input validation

    def post(self, request, order_id):
        try:
            order = get_object_or_404(Order, pk=order_id, user=request.user)
        except ValueError:
             return Response({"detail": "Invalid Order ID format."}, status=status.HTTP_400_BAD_REQUEST)

        if order.status != Order.OrderStatus.AWAITING_OTP_VERIFICATION:
            return Response({"detail": "Order is not awaiting OTP verification."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        submitted_otp = serializer.validated_data['otp_code']

        if order.is_otp_valid(submitted_otp):
            order.is_otp_verified = True
            if order.order_requires_prescription and order.prescription_status != Order.PrescriptionStatus.VERIFIED:
                 order.status = Order.OrderStatus.AWAITING_PRESCRIPTION
            else:
                order.status = Order.OrderStatus.PROCESSING

            order.otp_code = None
            order.otp_expiry = None
            order.save(update_fields=['is_otp_verified', 'status', 'otp_code', 'otp_expiry'])

            response_serializer = OrderSerializer(order, context={'request': request})
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"detail": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)