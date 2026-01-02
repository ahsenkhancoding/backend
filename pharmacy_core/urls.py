from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/users/', include('users.urls')),
    path('api/', include('products.urls')),
    path('api/', include('orders.urls')),
    path('api/', include('cart.urls')),
    path('api/', include('addresses.urls')),
    path('api/', include('shipping_delivery.urls')),

    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema')),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

