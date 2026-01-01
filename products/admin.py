# backend/products/admin.py
import csv
import io # Required for decoding the uploaded file

from django import forms # Import forms
from django.contrib import admin, messages
from django.db import transaction, IntegrityError
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.utils.text import slugify # For generating slugs for category/brand
from django.utils.translation import gettext_lazy as _ # For messages & labels

from .models import Category, Brand, Product

# --- Form for CSV Upload (Used by both importers) ---
# Define this class only once
class CsvImportForm(forms.Form):
    csv_file = forms.FileField(label=_("Select CSV file"))


# =======================================
# Category Admin
# =======================================
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)} # Auto-populate slug from name

# =======================================
# Brand Admin
# =======================================
@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)} # Auto-populate slug from name

# =======================================
# Product Admin
# =======================================
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # --- Admin Display Configuration ---
    change_list_template = "admin/products/product/change_list.html" # Use custom template for import button

    list_display = (
        'name', 'sku', 'brand', 'category', 'selling_price', 'purchase_price', # Added purchase_price
        'requires_prescription', 'is_available', 'updated_at'
    )
    list_filter = (
        'category', 'brand', 'requires_prescription', 'is_available',
        'created_at', 'updated_at'
    )
    search_fields = ('name', 'sku', 'description', 'composition', 'brand__name', 'category__name')
    prepopulated_fields = {'slug': ('name',)} # Auto-populate slug from name
    autocomplete_fields = ['category', 'brand'] # Use dropdown search for FKs
    # Adjust list_editable based on your role logic in get_list_editable
    list_editable = ('selling_price', 'purchase_price', 'is_available')

    # --- URL Configuration ---
    def get_urls(self):
        urls = super().get_urls()
        # Define custom URL patterns
        custom_urls = [
            # --- General importer URL ---
            path(
                'import-csv/',
                self.admin_site.admin_view(self.import_csv_view), # Wrap view with admin permissions check
                name=f'{self.model._meta.app_label}_{self.model._meta.model_name}_import_csv'
            ),
            # --- Price update importer URL ---
            path(
                'update-prices-csv/',
                self.admin_site.admin_view(self.update_prices_csv_view),
                name=f'{self.model._meta.app_label}_{self.model._meta.model_name}_update_prices_csv'
            )
        ]
        # Prepend custom URLs to the default admin URLs
        return custom_urls + urls

    # --- View to Handle General CSV Import (Conditional Update Logic) ---
    def import_csv_view(self, request):
        """
        Displays an upload form (GET) and processes the general CSV file (POST).
        Updates only fields that have non-blank values in the CSV.
        """
        opts = self.model._meta

        if request.method == "POST":
            form = CsvImportForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = request.FILES["csv_file"]

                if not csv_file.name.endswith('.csv'):
                    self.message_user(request, _("Invalid file type. Please upload a CSV file."), messages.ERROR)
                    return redirect(request.path_info)

                try:
                    decoded_file = io.TextIOWrapper(csv_file.file, encoding='utf-8', errors='replace')
                    reader = csv.DictReader(decoded_file)

                    # --- Expected CSV Headers (General Import) ---
                    expected_headers = [
                        'sku', 'name', 'slug', 'description', 'composition',
                        'usage_instructions', 'warnings', 'mrp', 'purchase_price',
                        'selling_price', 'image_url', 'requires_prescription',
                        'is_available', 'category_name', 'brand_name'
                    ]
                    if not reader.fieldnames:
                         self.message_user(request, _("CSV file is empty or header row is missing."), messages.ERROR)
                         return redirect(request.path_info)

                    csv_headers = set(h.strip() for h in reader.fieldnames)
                    expected_set = set(expected_headers)
                    if not expected_set.issubset(csv_headers):
                        missing = expected_set - csv_headers
                        error_msg = _("CSV header mismatch.")
                        if missing:
                            error_msg += _(" Missing required headers: {}.").format(', '.join(missing))
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
                                    errors.append(_("Row {}: Missing SKU. Skipping row.").format(i))
                                    continue

                                product_data = {} # Reset for each row

                                # --- Handle Text fields ---
                                for field_key, csv_header in [
                                    ('name', 'name'), ('slug', 'slug'), ('description', 'description'),
                                    ('composition', 'composition'), ('usage_instructions', 'usage_instructions'),
                                    ('warnings', 'warnings'), ('image_url', 'image_url')
                                ]:
                                    value = row.get(csv_header, '').strip()
                                    if value: product_data[field_key] = value

                                # --- Handle Numeric fields ---
                                for field_key, csv_header in [
                                    ('mrp', 'mrp'), ('purchase_price', 'purchase_price'), ('selling_price', 'selling_price')
                                ]:
                                    price_str = row.get(csv_header)
                                    if price_str is not None:
                                        price_str = price_str.strip()
                                        if price_str != '':
                                            try: product_data[field_key] = float(price_str)
                                            except (ValueError, TypeError): errors.append(_("Row {} (SKU: {}): Invalid numeric value '{}' for {}. Field skipped.").format(i, sku, price_str, csv_header))

                                # --- Handle Boolean fields ---
                                for field_key, csv_header in [
                                    ('requires_prescription', 'requires_prescription'), ('is_available', 'is_available')
                                ]:
                                    bool_str = row.get(csv_header)
                                    if bool_str is not None:
                                        bool_str = bool_str.strip()
                                        if bool_str != '': product_data[field_key] = bool_str.lower() in ('true', '1', 'yes', 'y', 'on')

                                # --- Handle Foreign Keys ---
                                category_name = row.get('category_name', '').strip()
                                if category_name:
                                    try:
                                        category, _ = Category.objects.get_or_create( name__iexact=category_name, defaults={'name': category_name, 'slug': slugify(category_name)})
                                        product_data['category'] = category
                                    except Exception as e: errors.append(_("Row {} (SKU: {}): Error finding/creating category '{}': {}").format(i, sku, category_name, e))

                                brand_name = row.get('brand_name', '').strip()
                                if brand_name:
                                    try:
                                        brand, _ = Brand.objects.get_or_create(name__iexact=brand_name, defaults={'name': brand_name, 'slug': slugify(brand_name)})
                                        product_data['brand'] = brand
                                    except Exception as e: errors.append(_("Row {} (SKU: {}): Error finding/creating brand '{}': {}").format(i, sku, brand_name, e))

                                # --- Perform update/create ---
                                if product_data:
                                    product, created = Product.objects.update_or_create( sku=sku, defaults=product_data)
                                    if created: products_created += 1
                                    else: products_updated += 1
                                else: pass # No valid data to update besides maybe SKU

                            except IntegrityError as e: errors.append(_("Row {} (SKU: {}): Database integrity error - {}").format(i, sku, e))
                            except Exception as e: errors.append(_("Row {} (SKU: {}): Unexpected error - {}").format(i, sku, e))

                    # --- Report Results ---
                    processed_msg = _("Processed {} rows.").format(rows_processed)
                    self.message_user(request, processed_msg, messages.INFO)
                    if products_created > 0: self.message_user(request, _("{} products created successfully.").format(products_created), messages.SUCCESS)
                    if products_updated > 0: self.message_user(request, _("{} products updated successfully.").format(products_updated), messages.SUCCESS)
                    if errors:
                        for error in errors: self.message_user(request, error, messages.WARNING)
                        self.message_user(request, _("Import completed with some issues. Please review messages."), messages.WARNING)
                    elif products_created == 0 and products_updated == 0 and rows_processed > 0: self.message_user(request, _("No products needed creating or updating based on the CSV content."), messages.WARNING)
                    elif not errors: self.message_user(request, _("CSV import finished successfully."), messages.INFO)

                    changelist_url = reverse(f'admin:{opts.app_label}_{opts.model_name}_changelist')
                    return redirect(changelist_url)

                except Exception as e:
                    self.message_user(request, _("An critical error occurred during file processing: {}").format(e), messages.ERROR)
                    return redirect(request.path_info)
            else: pass # Invalid form (no file), render form again
        else:
            # --- Render the Form for GET request ---
            form = CsvImportForm()

        context = {
            **self.admin_site.each_context(request),
            'title': _('Import/Update Products from CSV'),
            'opts': opts,
            'form': form,
            'has_view_permission': self.has_view_permission(request),
            'has_add_permission': self.has_add_permission(request),
            'has_change_permission': self.has_change_permission(request),
        }
        return render(request, 'admin/products/product/import_csv_form.html', context)


    # --- View to Handle PRICE Update CSV ---
    def update_prices_csv_view(self, request):
        """
        Displays an upload form (GET) and processes CSV for PRICE updates only (POST).
        Expects columns: sku, purchase_price, selling_price.
        """
        opts = self.model._meta
        form = CsvImportForm() # Use the same simple form for file upload

        if request.method == "POST":
            form = CsvImportForm(request.POST, request.FILES) # Re-bind form on POST
            if form.is_valid():
                csv_file = request.FILES["csv_file"]

                if not csv_file.name.endswith('.csv'):
                    self.message_user(request, _("Invalid file type. Please upload a CSV file."), messages.ERROR)
                    return redirect(request.path_info)

                try:
                    decoded_file = io.TextIOWrapper(csv_file.file, encoding='utf-8', errors='replace')
                    reader = csv.DictReader(decoded_file)

                    # --- Define Expected Headers for Price Update ---
                    expected_headers = ['sku', 'purchase_price', 'selling_price']
                    if not reader.fieldnames:
                         self.message_user(request, _("CSV file is empty or header row is missing."), messages.ERROR)
                         return redirect(request.path_info)

                    # --- Validate Headers ---
                    csv_headers = set(h.strip() for h in reader.fieldnames)
                    expected_set = set(expected_headers)
                    if not expected_set.issubset(csv_headers):
                        missing = expected_set - csv_headers
                        error_msg = _("Price update CSV header mismatch.")
                        if missing:
                            error_msg += _(" Missing required headers: {}.").format(', '.join(missing))
                        self.message_user(request, error_msg, messages.ERROR)
                        return redirect(request.path_info)

                    # --- Initialize Counters and Error List ---
                    products_updated = 0
                    rows_processed = 0
                    errors = []

                    # --- Process Rows within a Transaction ---
                    with transaction.atomic():
                        for i, row in enumerate(reader, start=2): # Start row count from 2
                            rows_processed += 1
                            sku = row.get('sku', '').strip()
                            if not sku:
                                errors.append(_("Row {}: Missing SKU. Skipping row.").format(i))
                                continue

                            try:
                                # Find the product - raise DoesNotExist if not found
                                product = Product.objects.get(sku=sku)

                                # --- Process Prices (Only if present and valid) ---
                                update_fields = {} # Store fields to update for this product
                                purchase_price_str = row.get('purchase_price', '').strip()
                                selling_price_str = row.get('selling_price', '').strip()

                                if purchase_price_str: # Check if purchase_price provided
                                    try:
                                        update_fields['purchase_price'] = float(purchase_price_str)
                                    except (ValueError, TypeError):
                                        errors.append(_("Row {} (SKU: {}): Invalid purchase price '{}'. Field skipped.").format(i, sku, purchase_price_str))

                                if selling_price_str: # Check if selling_price provided
                                    try:
                                        update_fields['selling_price'] = float(selling_price_str)
                                    except (ValueError, TypeError):
                                         errors.append(_("Row {} (SKU: {}): Invalid selling price '{}'. Field skipped.").format(i, sku, selling_price_str))

                                # --- Update Product if any valid prices were found ---
                                if update_fields:
                                    for field, value in update_fields.items():
                                        setattr(product, field, value) # Set the attribute on the model instance
                                    product.save(update_fields=list(update_fields.keys())) # Efficiently save only changed fields (convert keys to list)
                                    products_updated += 1
                                # else: No valid prices to update for this row

                            except Product.DoesNotExist:
                                errors.append(_("Row {}: Product with SKU '{}' not found. Skipping row.").format(i, sku))
                            except Exception as e:
                                # Catch any other unexpected errors during row processing
                                errors.append(_("Row {} (SKU: {}): Unexpected error - {}").format(i, sku, e))

                    # --- Report Results to User ---
                    processed_msg = _("Processed {} rows for price update.").format(rows_processed)
                    self.message_user(request, processed_msg, messages.INFO)

                    if products_updated > 0:
                        self.message_user(request, _("{} products' prices updated successfully.").format(products_updated), messages.SUCCESS)

                    if errors: # Display any row-level errors or warnings
                        for error in errors:
                            self.message_user(request, error, messages.WARNING) # Use WARNING for row errors
                        self.message_user(request, _("Price update completed with some issues. Please review messages."), messages.WARNING)
                    elif products_updated == 0 and rows_processed > 0:
                         self.message_user(request, _("No product prices were updated. Check SKUs and price data in the CSV."), messages.WARNING)
                    elif not errors: # No errors and updates occurred
                        self.message_user(request, _("Price update finished successfully."), messages.INFO)

                    # Redirect back to the product change list view
                    changelist_url = reverse(f'admin:{opts.app_label}_{opts.model_name}_changelist')
                    return redirect(changelist_url)

                except Exception as e:
                    # Catch critical errors during file reading/setup
                    self.message_user(request, _("An critical error occurred during file processing: {}").format(e), messages.ERROR)
                    return redirect(request.path_info) # Redirect back to import form
            else:
                # Form is invalid (e.g., no file selected), form errors shown by template
                pass # Fall through to render the form again below

        # --- Prepare Context for Rendering the Template (GET request or invalid POST) ---
        context = {
            **self.admin_site.each_context(request),
            'title': _('Update Product Prices from CSV'), # Specific title
            'opts': opts,
            'form': form, # Pass the bound (if POST and invalid) or unbound (if GET) form
            'has_view_permission': self.has_view_permission(request), # Needed for base template
            'has_change_permission': self.has_change_permission(request), # Price update needs change permission
        }
        # Render the specific template for this view
        return render(request, 'admin/products/product/update_prices_form.html', context)


    # --- Role-Based Field Customization Methods ---

    def get_fieldsets(self, request, obj=None):
        # Default fieldsets for superuser/full access
        fieldsets = (
            (None, {'fields': ('name', 'slug', 'sku', 'brand', 'category')}),
            ('Details & Pricing', {'fields': ('description', 'composition', 'usage_instructions', 'warnings', 'mrp', 'purchase_price', 'selling_price', 'image_url')}),
            ('Status & Requirements', {'fields': ('requires_prescription', 'is_available')}),
            ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
        )
        # Customize for 'Content Writers' group
        if request.user.groups.filter(name='Content Writers').exists() and not request.user.is_superuser:
             fieldsets = (
                 (None, {'fields': ('name', 'brand', 'category')}), # Read-only context? Check readonly fields
                 ('Content Editing', {'fields': ('description', 'composition', 'usage_instructions', 'warnings')}),
             )
        # Add elif for 'Inventory Managers' if they need different fieldsets
        # elif request.user.groups.filter(name='Inventory Managers').exists() and not request.user.is_superuser:
        #     fieldsets = (...)
        return fieldsets


    def get_readonly_fields(self, request, obj=None):
        # Default read-only fields
        readonly_fields = ['created_at', 'updated_at']
        # Make fields read-only for Content Writers except the ones they can edit
        if request.user.groups.filter(name='Content Writers').exists() and not request.user.is_superuser:
             readonly_fields.extend(['slug', 'sku', 'brand', 'category', 'mrp', 'purchase_price', 'selling_price', 'image_url', 'requires_prescription', 'is_available'])
        # Make fields read-only for Inventory Managers except the ones they edit
        elif request.user.groups.filter(name='Inventory Managers').exists() and not request.user.is_superuser:
              # Inventory Managers CAN edit prices (purchase, selling, mrp?), sku, availability
              # Make descriptive fields read-only for them
              readonly_fields.extend(['name', 'slug', 'brand', 'category', 'description', 'composition', 'usage_instructions', 'warnings', 'image_url', 'requires_prescription']) # Example
        return readonly_fields


    def get_list_editable(self, request):
        # Allow list editing only for specific groups or superuser
         # Check for specific group or superuser status
         user_is_manager = request.user.groups.filter(name='Inventory Managers').exists()
         if user_is_manager or request.user.is_superuser:
             # Allow editing prices and availability in the list view
             return ('selling_price', 'purchase_price', 'is_available')
         return () # No list editing for others by default