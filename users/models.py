# backend/users/models.py
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
import uuid

class CustomUserManager(BaseUserManager):
    """
    Custom manager for the CustomUser model where the phone number is the unique identifier.
    """
    def create_user(self, phone_number, password=None, **extra_fields):
        """
        Creates and saves a User with the given phone number and password.
        """
        if not phone_number:
            raise ValueError('The Phone Number must be set')
        
        user = self.model(phone_number=phone_number, **extra_fields)
        # Use set_password to hash the password properly
        if password:
             user.set_password(password)
        else:
             # Set unusable password if none provided (e.g., for OTP only)
             user.set_unusable_password() 
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password, **extra_fields):
        """
        Creates and saves a superuser with the given phone number and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True) # Superusers should be active

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        # Ensure name fields exist even if empty for superuser creation via command line
        extra_fields.setdefault('name', '') 

        return self.create_user(phone_number, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom User Model using phone number as the primary identifier.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=255, blank=True)
    
    is_staff = models.BooleanField(default=False) # Required for Django Admin access
    is_active = models.BooleanField(default=True) # Designates whether user account is active
    is_superuser = models.BooleanField(default=False) # Superuser flag (set via PermissionsMixin)

    date_joined = models.DateTimeField(default=timezone.now)

    # Tell Django which field to use as the username
    USERNAME_FIELD = 'phone_number' 
    # Fields required when creating user via createsuperuser command (besides username/password)
    # 'name' is included here so createsuperuser prompts for it (optional). Email could be added too.
    REQUIRED_FIELDS = ['name'] 

    objects = CustomUserManager() # Link the custom manager

    def __str__(self):
        return f"{self.name} ({self.phone_number})" if self.name else self.phone_number

    # PermissionsMixin provides group/permission fields and methods like has_perm, has_module_perms