# backend/products/management/commands/import_products_csv.py
import csv
import io # To handle in-memory file from admin upload
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction # For atomic updates
from products.models import Product, Category, Brand # Import necessary models

class Command(BaseCommand):
    help = 'Imports or updates products from a CSV file with columns: sku, name, category_name, brand_name, mrp, selling_price, description, composition, usage_instructions, warnings, requires_prescription (True/False), is_available (True/False), image_url'

    def add_arguments(self, parser):
        # Argument for direct file path (optional, for command-line use)
        parser.add_argument('--filepath', type=str, help='The path to the CSV file to import.')
        # Argument to receive file content (used by admin action)
        parser.add_argument('--filecontent', type=str, help='CSV file content as a string.')

    @transaction.atomic # Ensure all updates succeed or fail together
    def handle(self, *args, **options):
        filepath = options.get('filepath')
        filecontent = options.get('filecontent')

        if not filepath and not filecontent:
            raise CommandError('Please provide either --filepath or --filecontent.')
        
        if filepath and filecontent:
             raise CommandError('Provide either --filepath or --filecontent, not both.')

        self.stdout.write(self.style.NOTICE('Starting product import/update...'))
        
        processed_count = 0
        created_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []

        try:
            if filepath:
                # Read from file path
                 with open(filepath, mode='r', encoding='utf-8-sig') as csvfile: # Use utf-8-sig to handle potential BOM
                    reader = csv.DictReader(csvfile)
                    if not reader.fieldnames:
                        raise CommandError(f"CSV file '{filepath}' seems empty or has no header.")
                    required_fields = ['sku', 'name', 'selling_price'] # Minimum required
                    if not all(field in reader.fieldnames for field in required_fields):
                        raise CommandError(f"CSV missing required columns: {required_fields}. Found: {reader.fieldnames}")
                    
                    for row_num, row in enumerate(reader, start=2): # start=2 for header row
                        result = self.process_row(row, row_num)
                        if result == 'created': created_count += 1
                        elif result == 'updated': updated_count += 1
                        elif result == 'skipped': skipped_count += 1
                        elif isinstance(result, str) and result.startswith('error'): errors.append(result)
                        processed_count += 1

            elif filecontent:
                 # Read from string content (passed from admin)
                 csvfile = io.StringIO(filecontent)
                 reader = csv.DictReader(csvfile)
                 if not reader.fieldnames:
                        raise CommandError("Uploaded CSV data seems empty or has no header.")
                 required_fields = ['sku', 'name', 'selling_price'] # Minimum required
                 if not all(field in reader.fieldnames for field in required_fields):
                     raise CommandError(f"CSV missing required columns: {required_fields}. Found: {reader.fieldnames}")
                 
                 for row_num, row in enumerate(reader, start=2):
                    result = self.process_row(row, row_num)
                    if result == 'created': created_count += 1
                    elif result == 'updated': updated_count += 1
                    elif result == 'skipped': skipped_count += 1
                    elif isinstance(result, str) and result.startswith('error'): errors.append(result)
                    processed_count += 1

        except FileNotFoundError:
            raise CommandError(f'File not found at path: {filepath}')
        except Exception as e:
            raise CommandError(f'An unexpected error occurred: {e}')

        # Report Summary
        self.stdout.write(self.style.SUCCESS(f'Import finished. Processed: {processed_count}'))
        self.stdout.write(self.style.SUCCESS(f'Created: {created_count}, Updated: {updated_count}, Skipped: {skipped_count}'))
        if errors:
             self.stdout.write(self.style.WARNING(f'Errors ({len(errors)}):'))
             for error in errors[:20]: # Show first 20 errors
                 self.stderr.write(self.style.ERROR(error))
             if len(errors) > 20:
                  self.stderr.write(self.style.ERROR(f"... and {len(errors)-20} more errors."))


    def process_row(self, row, row_num):
        """ Processes a single row from the CSV data. """
        sku = row.get('sku', '').strip()
        name = row.get('name', '').strip()
        selling_price_str = row.get('selling_price', '').strip()

        # Basic validation
        if not sku: return f"error: Row {row_num}: Missing SKU."
        if not name: return f"error: Row {row_num}: Missing Name for SKU {sku}."
        if not selling_price_str: return f"error: Row {row_num}: Missing Selling Price for SKU {sku}."

        try:
            selling_price = Decimal(selling_price_str)
        except InvalidOperation:
            return f"error: Row {row_num}: Invalid Selling Price '{selling_price_str}' for SKU {sku}."

        # Optional fields - handle potential errors or missing values gracefully
        category_name = row.get('category_name', '').strip()
        brand_name = row.get('brand_name', '').strip()
        mrp_str = row.get('mrp', '').strip()
        description = row.get('description', '').strip()
        composition = row.get('composition', '').strip()
        usage = row.get('usage_instructions', '').strip()
        warnings = row.get('warnings', '').strip()
        req_rx_str = row.get('requires_prescription', 'False').strip().capitalize()
        is_avail_str = row.get('is_available', 'True').strip().capitalize()
        image_url = row.get('image_url', '').strip()

        # --- Get or Create Category/Brand ---
        category = None
        if category_name:
            category, _ = Category.objects.get_or_create(name=category_name, defaults={'slug': category_name.lower().replace(' ', '-')}) # Basic slug generation

        brand = None
        if brand_name:
            brand, _ = Brand.objects.get_or_create(name=brand_name, defaults={'slug': brand_name.lower().replace(' ', '-')})

        # --- Prepare data for Product update_or_create ---
        defaults = {
            'name': name,
            'selling_price': selling_price,
            'category': category,
            'brand': brand,
            'description': description or '', # Use empty string if blank
            'composition': composition or '',
            'usage_instructions': usage or '',
            'warnings': warnings or '',
            'requires_prescription': req_rx_str == 'True',
            'is_available': is_avail_str == 'True',
            'image_url': image_url or '',
        }
        
        # Handle optional MRP
        if mrp_str:
            try:
                defaults['mrp'] = Decimal(mrp_str)
            except InvalidOperation:
                 self.stdout.write(self.style.WARNING(f"Row {row_num}: Skipping invalid MRP '{mrp_str}' for SKU {sku}."))

        # Generate slug if creating (or update if name changed?) - simple version
        defaults['slug'] = sku.lower() # Use SKU as base for slug initially, ensure uniqueness if needed

        try:
            product, created = Product.objects.update_or_create(
                sku=sku, # Use SKU to find existing product
                defaults=defaults # Fields to set/update
            )
            return 'created' if created else 'updated'
        except Exception as e:
            return f"error: Row {row_num}: Failed to save SKU {sku}. Error: {e}"