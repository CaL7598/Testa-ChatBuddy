from django.conf import settings
from django.http import HttpResponse

# Google Search Console — HTML file verification (keep in sync with filename)
GOOGLE_HTML_VERIFICATION = 'googlef9819ca33b10c69b.html'
GOOGLE_HTML_VERIFICATION_BODY = (
    f'google-site-verification: {GOOGLE_HTML_VERIFICATION}'
)


def google_html_verification(request):
    return HttpResponse(GOOGLE_HTML_VERIFICATION_BODY, content_type='text/html')


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
