# backend/products/models.py
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

# =======================================
# Category Model
# =======================================
class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    # Slug is auto-generated if left blank
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ['name']

# =======================================
# Brand Model
# =======================================
class Brand(models.Model):
    name = models.CharField(max_length=255, unique=True)
    # Slug is auto-generated if left blank
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Brand")
        verbose_name_plural = _("Brands")
        ordering = ['name']

# =======================================
# Product Model
# =======================================
class Product(models.Model):
    # --- Basic Info ---
    name = models.CharField(max_length=255)
    # Slug is auto-generated if left blank
    slug = models.SlugField(max_length=255, unique=True, blank=True, help_text=_("Unique URL-friendly identifier. Auto-generated if left blank."))
    # SKU should be required and unique
    sku = models.CharField(max_length=100, unique=True, help_text=_("Unique Stock Keeping Unit"))
    # Brand and Category are optional foreign keys
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')

    # --- Detailed Info (Optional Text Fields) ---
    # blank=True allows empty values in forms/admin
    description = models.TextField(blank=True)
    composition = models.TextField(blank=True, help_text=_("Ingredients or chemical composition."))
    usage_instructions = models.TextField(blank=True)
    warnings = models.TextField(blank=True)

    # --- Pricing ---
    # Ensure these are DecimalFields
    mrp = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text=_("Maximum Retail Price"))
    # The newly added field - make it optional for now
    purchase_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True, # Allows NULL in the database
        blank=True, # Allows empty in forms/admin
        help_text=_("Price at which the product was procured.")
    )
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, help_text=_("Price at which the product is sold."))

    # --- Image (Optional URL) ---
    # blank=True and null=True make this optional
    image_url = models.URLField(max_length=1024, blank=True, null=True)

    # --- Status & Requirements ---
    # Booleans generally don't need null=True unless you need a "null" state
    requires_prescription = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True, help_text=_("Is the product available for sale?"))

    # --- Timestamps (Managed by Django) ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # --- !!! ADD BACK ANY OTHER CUSTOM FIELDS YOU NEEDED HERE !!! ---
    # If you had fields like formulation, health_concerns, etc., add their definitions back here.
    # Example:
    # formulation = models.CharField(max_length=100, blank=True)
    # ------------------------------------------------------------

    def save(self, *args, **kwargs):
        if not self.slug and self.name: # Generate slug only if blank and name exists
            base_slug = slugify(self.name)
            unique_slug = base_slug
            # Basic uniqueness check (a better check might involve querying)
            num = 1
            while Product.objects.filter(slug=unique_slug).exclude(pk=self.pk).exists():
                unique_slug = f'{base_slug}-{num}'
                num += 1
            self.slug = unique_slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.sku})"

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ['name', 'sku']
        # Define indexes for commonly filtered/ordered fields
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['name']),
            models.Index(fields=['category']),
            models.Index(fields=['brand']),
            models.Index(fields=['is_available']), # If frequently filtered
        ]