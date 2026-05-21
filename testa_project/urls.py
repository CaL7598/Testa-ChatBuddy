from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('testa_app.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # Demo deployments (e.g. Render): serve uploads without a separate CDN
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)