# backend/orders/otp_service.py
import random
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)

# Define OTP settings (could be moved to settings.py)
OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 5

def generate_otp(length=OTP_LENGTH):
    """Generates a random numeric OTP code."""
    # Ensure OTP is purely numeric and has leading zeros if needed
    return "".join([str(random.randint(0, 9)) for _ in range(length)])

def send_order_otp(order):
    """
    Generates OTP, saves it to the order, and attempts to send it via SMS.
    Returns True if OTP sending process initiated, False otherwise.
    """
    if not order or not order.shipping_phone_number:
        logger.error(f"Cannot send OTP: Order {order.id if order else 'N/A'} missing or no phone number.")
        return False

    try:
        otp = generate_otp()
        expiry_time = timezone.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)

        # TODO: Implement OTP Hashing before saving for security
        # Example: order.otp_hash = hash_otp_function(otp)
        order.otp_code = otp # Storing plain text for now (INSECURE)
        order.otp_expiry = expiry_time
        order.is_otp_verified = False # Reset verification status
        order.status = order.OrderStatus.AWAITING_OTP_VERIFICATION # Update status
        order.save(update_fields=['otp_code', 'otp_expiry', 'is_otp_verified', 'status'])

        # --- Placeholder for Actual SMS Sending ---
        # Replace this section with your chosen SMS Gateway API call
        phone_number = order.shipping_phone_number
        message = f"Your order confirmation code is {otp}. It expires in {OTP_EXPIRY_MINUTES} minutes."

        logger.info(f"Attempting to send OTP {otp} to {phone_number} for Order {order.id}")
        logger.debug(f"SMS Message Content: {message}") # Log message content only if DEBUG=True

        # --- BEGIN SMS Gateway Integration Placeholder ---
        try:
            # Example using a fictional function `call_sms_gateway`
            # success = call_sms_gateway(api_key=settings.SMS_API_KEY, to=phone_number, message=message)

            # *** SIMULATE SUCCESS/FAILURE FOR NOW ***
            # Set success=True to simulate successful sending in development
            success = True
            # Set success=False to simulate a failure
            # success = False

            if success:
                logger.info(f"SMS potentially sent to {phone_number} for Order {order.id}")
                return True # Indicate sending process was successful
            else:
                logger.error(f"SMS Gateway failed to send OTP to {phone_number} for Order {order.id}")
                # Optionally: Handle failure (e.g., retry later, notify admin)
                return False # Indicate sending failed

        except Exception as e:
            logger.exception(f"Error calling SMS Gateway for Order {order.id}: {e}")
            return False
        # --- END SMS Gateway Integration Placeholder ---

    except Exception as e:
        logger.exception(f"Error generating/saving OTP for Order {order.id}: {e}")
        return False
    