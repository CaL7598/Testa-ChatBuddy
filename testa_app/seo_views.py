from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone

# Google Search Console — HTML file verification (keep in sync with filename)
GOOGLE_HTML_VERIFICATION = 'googlef9819ca33b10c69b.html'
GOOGLE_HTML_VERIFICATION_BODY = (
    f'google-site-verification: {GOOGLE_HTML_VERIFICATION}'
)


def google_html_verification(request):
    return HttpResponse(GOOGLE_HTML_VERIFICATION_BODY, content_type='text/html')


def sitemap_xml(request):
    """Static sitemap (avoids django.contrib.sites 500 on Render)."""
    base = getattr(settings, 'SITE_URL', '').strip().rstrip('/')
    if not base:
        base = request.build_absolute_uri('/').rstrip('/')
    today = timezone.now().date().isoformat()
    pages = [
        ('/', '1.0', 'weekly'),
        ('/about/', '0.8', 'weekly'),
        ('/register/', '0.5', 'monthly'),
        ('/login/', '0.5', 'monthly'),
    ]
    url_entries = []
    for path, priority, changefreq in pages:
        loc = f'{base}{path}'
        url_entries.append(
            f'  <url>\n'
            f'    <loc>{loc}</loc>\n'
            f'    <lastmod>{today}</lastmod>\n'
            f'    <changefreq>{changefreq}</changefreq>\n'
            f'    <priority>{priority}</priority>\n'
            f'  </url>'
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + '\n'.join(url_entries)
        + '\n</urlset>\n'
    )
    return HttpResponse(xml, content_type='application/xml')


def robots_txt(request):
    site_url = getattr(settings, 'SITE_URL', '').strip().rstrip('/')
    lines = [
        'User-agent: *',
        'Allow: /$',
        'Allow: /about/',
        'Allow: /register/',
        'Allow: /login/',
        'Disallow: /admin/',
        'Disallow: /question_answer/',
        'Disallow: /analytics/',
        'Disallow: /pdf_upload/',
        'Disallow: /profile/',
        'Disallow: /search/',
        'Disallow: /bookmarks/',
        'Disallow: /recommendations/',
        'Disallow: /quiz/',
        'Disallow: /flashcards/',
        'Disallow: /summary/',
        'Disallow: /study-guide/',
        'Disallow: /password-reset',
        'Disallow: /verify-email/',
        'Disallow: /health/',
    ]
    if site_url:
        lines.append(f'Sitemap: {site_url}/sitemap.xml')
    return HttpResponse('\n'.join(lines) + '\n', content_type='text/plain')
