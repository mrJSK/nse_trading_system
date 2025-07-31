# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings # Import settings
from django.conf.urls.static import static

from apps.core.views import health_check_view # Import static and media file serving utilities

urlpatterns = [
    path('admin/', admin.site.urls),
    # Add other app URLs here if you have them, e.g.:
    # path('api/', include('apps.core.urls')),
    # path('market-data/', include('apps.market_data_service.urls')),
    path('health/', health_check_view, name='health_check'),
    path('', include('apps.dashboard.urls')),  # Dashboard as home page
    # path('dashboard/', include('apps.dashboard.urls')),  # Or specific dashboard path
]

# Only include debug_toolbar URLs if DEBUG is True
# This block should be placed AFTER your other urlpatterns but BEFORE any 404/500 handlers
if settings.DEBUG:
    import debug_toolbar # Import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns

# Serve static and media files during development
# This is typically placed at the very end of urlpatterns in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)