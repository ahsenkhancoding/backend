# backend/products/admin.py
import csv
import io # Required for decoding the uploaded file

from django import forms # Import forms
from django.contrib import admin, messages
from django.db import transaction, IntegrityError
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.utils.text import slugify # For generating slugs for category/brand
from django.utils.translation import gettext as _t # Using _t to avoid conflict with loop variables

from .models import Category, Brand, Product

# --- Form for CSV Upload (Used by both importers) ---
class CsvImportForm(forms.Form):
    csv_file = forms.FileField(label="Select CSV file")


# =======================================
# Category Admin
# =======================================
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)} 

# =======================================
# Brand Admin
# =======================================
@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)} 

# =======================================
# Product Admin
# =======================================
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # --- Admin Display Configuration ---
    change_list_template = "admin/products/product/change_list.html" 

    list_display = (
        'name', 'sku', 'brand', 'category', 'selling_price', 'purchase_price', 
        'requires_prescription', 'is_available', 'updated_at'
    )
    list_filter = (
        'category', 'brand', 'requires_prescription', 'is_available',
        'created_at', 'updated_at'
    )
    search_fields = ('name', 'sku', 'description', 'composition', 'brand__name', 'category__name')
    prepopulated_fields = {'slug': ('name',)} 
    autocomplete_fields = ['category', 'brand'] 
    list_editable = ('selling_price', 'purchase_price', 'is_available')

    # --- URL Configuration ---
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'import-csv/',
                self.admin_site.admin_view(self.import_csv_view), 
                name=f'{self.model._meta.app_label}_{self.model._meta.model_name}_import_csv'
            ),
            path(
                'update-prices-csv/',
                self.admin_site.admin_view(self.update_prices_csv_view),
                name=f'{self.model._meta.app_label}_{self.model._meta.model_name}_update_prices_csv'
            )
        ]
        return custom_urls + urls

    # --- View to Handle General CSV Import ---
    def import_csv_view(self, request):
        opts = self.model._meta

        if request.method == "POST":
            form = CsvImportForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = request.FILES["csv_file"]

                if not csv_file.name.endswith('.csv'):
                    self.message_user(request, "Invalid file type. Please upload a CSV file.", messages.ERROR)
                    return redirect(request.path_info)

                try:
                    decoded_file = io.TextIOWrapper(csv_file.file, encoding='utf-8', errors='replace')
                    reader = csv.DictReader(decoded_file)

                    expected_headers = [
                        'sku', 'name', 'slug', 'description', 'composition',
                        'usage_instructions', 'warnings', 'mrp', 'purchase_price',
                        'selling_price', 'image_url', 'requires_prescription',
                        'is_available', 'category_name', 'brand_name'
                    ]
                    if not reader.fieldnames:
                         self.message_user(request, "CSV file is empty or header row is missing.", messages.ERROR)
                         return redirect(request.path_info)

                    csv_headers = set(h.strip() for h in reader.fieldnames)
                    expected_set = set(expected_headers)
                    if not expected_set.issubset(csv_headers):
                        missing = expected_set - csv_headers
                        error_msg = f"CSV header mismatch. Missing: {', '.join(missing)}"
                        self.message_user(request, error_msg, messages.ERROR)
                        return redirect(request.path_info)

                    products_created = 0
                    products_updated = 0
                    rows_processed = 0
                    errors = []

                    with transaction.atomic():
                        for i, row in enumerate(reader, start=2):
                            rows_processed += 1
                            try:
                                sku = row.get('sku', '').strip()
                                if not sku:
                                    errors.append(f"Row {i}: Missing SKU. Skipping row.")
                                    continue

                                product_data = {} 

                                for field_key, csv_header in [
                                    ('name', 'name'), ('slug', 'slug'), ('description', 'description'),
                                    ('composition', 'composition'), ('usage_instructions', 'usage_instructions'),
                                    ('warnings', 'warnings'), ('image_url', 'image_url')
                                ]:
                                    value = row.get(csv_header, '').strip()
                                    if value: product_data[field_key] = value

                                for field_key, csv_header in [
                                    ('mrp', 'mrp'), ('purchase_price', 'purchase_price'), ('selling_price', 'selling_price')
                                ]:
                                    price_str = row.get(csv_header)
                                    if price_str is not None:
                                        price_str = price_str.strip()
                                        if price_str != '':
                                            try: product_data[field_key] = float(price_str)
                                            except (ValueError, TypeError): errors.append(f"Row {i} (SKU: {sku}): Invalid numeric value '{price_str}' for {csv_header}.")

                                for field_key, csv_header in [
                                    ('requires_prescription', 'requires_prescription'), ('is_available', 'is_available')
                                ]:
                                    bool_str = row.get(csv_header)
                                    if bool_str is not None:
                                        bool_str = bool_str.strip()
                                        if bool_str != '': product_data[field_key] = bool_str.lower() in ('true', '1', 'yes', 'y', 'on')

                                category_name = row.get('category_name', '').strip()
                                if category_name:
                                    try:
                                        category, _cat_created = Category.objects.get_or_create( name__iexact=category_name, defaults={'name': category_name, 'slug': slugify(category_name)})
                                        product_data['category'] = category
                                    except Exception as e: errors.append(f"Row {i} (SKU: {sku}): Category error: {e}")

                                brand_name = row.get('brand_name', '').strip()
                                if brand_name:
                                    try:
                                        brand, _brand_created = Brand.objects.get_or_create(name__iexact=brand_name, defaults={'name': brand_name, 'slug': slugify(brand_name)})
                                        product_data['brand'] = brand
                                    except Exception as e: errors.append(f"Row {i} (SKU: {sku}): Brand error: {e}")

                                if product_data:
                                    product, created = Product.objects.update_or_create( sku=sku, defaults=product_data)
                                    if created: products_created += 1
                                    else: products_updated += 1

                            except IntegrityError as e: errors.append(f"Row {i} (SKU: {sku}): Integrity error - {e}")
                            except Exception as e: errors.append(f"Row {i} (SKU: {sku}): Error - {e}")

                    self.message_user(request, f"Processed {rows_processed} rows.", messages.INFO)
                    if products_created > 0: self.message_user(request, f"{products_created} products created.", messages.SUCCESS)
                    if products_updated > 0: self.message_user(request, f"{products_updated} products updated.", messages.SUCCESS)
                    if errors:
                        for error in errors[:10]: self.message_user(request, error, messages.WARNING)
                        self.message_user(request, "Import completed with issues. Check details.", messages.WARNING)

                    return redirect(reverse(f'admin:{opts.app_label}_{opts.model_name}_changelist'))

                except Exception as e:
                    self.message_user(request, f"Critical error: {e}", messages.ERROR)
                    return redirect(request.path_info)
        else:
            form = CsvImportForm()

        context = {
            **self.admin_site.each_context(request),
            'title': 'Import/Update Products from CSV',
            'opts': opts,
            'form': form,
        }
        return render(request, 'admin/products/product/import_csv_form.html', context)


    # --- View to Handle PRICE Update CSV ---
    def update_prices_csv_view(self, request):
        opts = self.model._meta
        form = CsvImportForm()

        if request.method == "POST":
            form = CsvImportForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = request.FILES["csv_file"]

                if not csv_file.name.endswith('.csv'):
                    self.message_user(request, "Please upload a CSV file.", messages.ERROR)
                    return redirect(request.path_info)

                try:
                    decoded_file = io.TextIOWrapper(csv_file.file, encoding='utf-8', errors='replace')
                    reader = csv.DictReader(decoded_file)
                    
                    products_updated = 0
                    rows_processed = 0
                    errors = []

                    with transaction.atomic():
                        for i, row in enumerate(reader, start=2):
                            rows_processed += 1
                            sku = row.get('sku', '').strip()
                            if not sku: continue

                            try:
                                product = Product.objects.get(sku=sku)
                                update_fields = {}
                                p_price = row.get('purchase_price', '').strip()
                                s_price = row.get('selling_price', '').strip()

                                if p_price: update_fields['purchase_price'] = float(p_price)
                                if s_price: update_fields['selling_price'] = float(s_price)

                                if update_fields:
                                    for field, value in update_fields.items():
                                        setattr(product, field, value)
                                    product.save(update_fields=list(update_fields.keys()))
                                    products_updated += 1

                            except Product.DoesNotExist:
                                errors.append(f"SKU {sku} not found.")
                            except Exception as e:
                                errors.append(f"Row {i} error: {e}")

                    self.message_user(request, f"Updated {products_updated} prices.", messages.SUCCESS)
                    return redirect(reverse(f'admin:{opts.app_label}_{opts.model_name}_changelist'))

                except Exception as e:
                    self.message_user(request, f"Error: {e}", messages.ERROR)
                    return redirect(request.path_info)

        context = {
            **self.admin_site.each_context(request),
            'title': 'Update Product Prices from CSV',
            'opts': opts,
            'form': form,
        }
        return render(request, 'admin/products/product/update_prices_form.html', context)

    # --- Role-Based Field Customization ---
    def get_fieldsets(self, request, obj=None):
        fieldsets = (
            (None, {'fields': ('name', 'slug', 'sku', 'brand', 'category')}),
            ('Pricing', {'fields': ('mrp', 'purchase_price', 'selling_price', 'image_url')}),
            ('Content', {'fields': ('description', 'composition', 'usage_instructions', 'warnings')}),
            ('Status', {'fields': ('requires_prescription', 'is_available')}),
        )
        return fieldsets

    def get_readonly_fields(self, request, obj=None):
        return ['created_at', 'updated_at']

    def get_list_editable(self, request):
        if request.user.is_superuser:
            return ('selling_price', 'purchase_price', 'is_available')
        return ()