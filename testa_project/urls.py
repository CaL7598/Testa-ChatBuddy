from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from testa_app.seo_views import google_html_verification, robots_txt, sitemap_xml

urlpatterns = [
    path('admin/', admin.site.urls),
    path('googlef9819ca33b10c69b.html', google_html_verification, name='google_html_verification'),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('sitemap.xml', sitemap_xml, name='sitemap_xml'),
    path('', include('testa_app.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # Demo deployments (e.g. Render): serve uploads without a separate CDN
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)