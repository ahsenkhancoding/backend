# backend/products/views.py
from rest_framework import viewsets, permissions, filters # Import filters
# Make sure DjangoFilterBackend is imported (should be present from previous step)
from django_filters.rest_framework import DjangoFilterBackend

from .models import Category, Brand, Product
from .serializers import CategorySerializer, BrandSerializer, ProductSerializer

# --- Keep CategoryViewSet and BrandViewSet as they are ---
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

class BrandViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Brand.objects.all().order_by('name')
    serializer_class = BrandSerializer
    permission_classes = [permissions.AllowAny]

# --- Modify ProductViewSet ---
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows Products to be viewed.
    Provides 'list' and 'retrieve' actions.
    Includes filtering, searching, and ordering capabilities.
    """
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]

    # --- ADD/UNCOMMENT Filtering/Searching/Ordering ---
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    # Define fields available for exact/lookup filtering (e.g., ?category=1 or ?brand__slug=healthplus)
    filterset_fields = {
        'category': ['exact'], # Allow filtering by category ID (e.g., ?category=1)
        'brand': ['exact'],    # Allow filtering by brand ID (e.g., ?brand=2)
        'category__slug': ['exact'], # Allow filtering by category slug (e.g., ?category__slug=pain-relief)
        'brand__slug': ['exact'],    # Allow filtering by brand slug (e.g., ?brand__slug=csv-pharma)
        'is_available': ['exact'],   # Allow filtering by availability (e.g., ?is_available=true)
        'requires_prescription': ['exact'], # Allow filtering by prescription status
        'selling_price': ['exact', 'lt', 'lte', 'gt', 'gte'], # Allow range filtering on price
    }
    # Define fields the SearchFilter will search across (e.g., ?search=vitamin)
    search_fields = ['name', 'sku', 'description', 'category__name', 'brand__name', 'composition']
    # Define fields the OrderingFilter allows sorting by (e.g., ?ordering=selling_price or ?ordering=-name)
    ordering_fields = ['selling_price', 'name', 'created_at', 'updated_at']
    ordering = ['name'] # Default ordering if not specified in the request
    # -------------------------------------------------

    def get_queryset(self):
        """
        List view shows available products by default.
        Detail view shows any product.
        Filtering/Searching is applied automatically by DRF based on filter_backends.
        """
        if self.action == 'list':
            # Base queryset for list view
            return Product.objects.filter(is_available=True) # Already filtered by filter_backends if needed
        # For retrieve (detail view), allow fetching any product
        return Product.objects.all()

    # If using slugs for lookup instead of IDs:
    # lookup_field = 'slug'