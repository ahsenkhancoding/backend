from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

# =======================================
# Category Model
# =======================================
class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
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
# Product Model (Full 1mg & SEO Upgrade)
# =======================================
class Product(models.Model):
    # --- Basic Info ---
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True, help_text=_("Unique URL-friendly identifier."))
    sku = models.CharField(max_length=100, unique=True, help_text=_("Unique Stock Keeping Unit"))
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')

    # --- 1mg-Style Content Sections ---
    description = models.TextField(blank=True, help_text=_("General patient-friendly introduction."))
    composition = models.TextField(blank=True, help_text=_("Salt Composition (e.g. Cefpodoxime Proxetil (200mg))"))
    benefits = models.TextField(blank=True, help_text=_("Uses and clinical benefits."))
    side_effects = models.TextField(blank=True, help_text=_("Comprehensive list of common and rare side effects."))
    how_to_use = models.TextField(blank=True, help_text=_("General instructions on consumption."))
    how_it_works = models.TextField(blank=True, help_text=_("Mechanism of action."))
    
    # --- Advanced Clinical Details (New) ---
    dosage = models.TextField(blank=True, help_text=_("Dosage guidelines by age and weight."))
    interactions = models.TextField(blank=True, help_text=_("Drug-drug and drug-food interactions."))
    missed_dose = models.TextField(blank=True, help_text=_("Instructions for a forgotten dose."))
    storage_conditions = models.TextField(blank=True, help_text=_("Storage temperature and environment advice."))
    quick_tips = models.TextField(blank=True, help_text=_("Expert advice and tips for the patient."))
    
    # --- Safety Advice Grid ---
    safety_alcohol = models.TextField(blank=True)
    safety_pregnancy = models.TextField(blank=True)
    safety_breastfeeding = models.TextField(blank=True)
    safety_driving = models.TextField(blank=True)
    safety_kidney = models.TextField(blank=True)
    safety_liver = models.TextField(blank=True)

    # --- Fact Box (Sidebar Data) ---
    fact_box_habit_forming = models.CharField(max_length=50, default="No")
    fact_box_therapeutic_class = models.CharField(max_length=255, blank=True)
    fact_box_chemical_class = models.CharField(max_length=255, blank=True)
    fact_box_action_class = models.CharField(max_length=255, blank=True)

    # --- SEO Fields (New) ---
    meta_title = models.CharField(max_length=255, blank=True, help_text=_("Search engine title (max 60 chars)."))
    meta_description = models.TextField(blank=True, help_text=_("Search engine description (max 155 chars)."))
    meta_keywords = models.TextField(blank=True, help_text=_("SEO keywords separated by commas."))

    # --- Pricing & Logistics ---
    mrp = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    image_url = models.URLField(max_length=1024, blank=True, null=True)
    requires_prescription = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)

    # --- Legacy Fields (Kept for compatibility) ---
    usage_instructions = models.TextField(blank=True) 
    warnings = models.TextField(blank=True)

    # --- Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.sku})"

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ['name', 'sku']
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['name']),
        ]
        