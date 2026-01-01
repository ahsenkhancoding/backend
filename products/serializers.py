# backend/products/serializers.py
from rest_framework import serializers
from .models import Category, Brand, Product

class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for the Category model.
    """
    class Meta:
        model = Category
        # Correct fields for Category model (assuming name, slug, id)
        fields = ['id', 'name', 'slug']

class BrandSerializer(serializers.ModelSerializer):
    """
    Serializer for the Brand model.
    """
    class Meta:
        model = Brand
        # Correct fields for Brand model (assuming name, slug, id)
        fields = ['id', 'name', 'slug']

class ProductSerializer(serializers.ModelSerializer):
    """
    Serializer for the Product model. Includes nested Category and Brand info.
    """
    # Use StringRelatedField to show category/brand names concisely
    category = serializers.StringRelatedField()
    brand = serializers.StringRelatedField()

    class Meta:
        model = Product
        # List all fields from the Product model you want to expose via the API
        fields = [
            'id', 'name', 'slug', 'sku', 'brand', 'category', 'description',
            'composition', 'usage_instructions', 'warnings', 'mrp',
            # 'purchase_price', # Decide if you want to expose purchase price
            'selling_price', 'image_url',
            'requires_prescription', 'is_available',
            'created_at', 'updated_at'
        ]
        # If you don't want purchase_price exposed, uncomment the line below instead of listing all fields
        # exclude = ['purchase_price']