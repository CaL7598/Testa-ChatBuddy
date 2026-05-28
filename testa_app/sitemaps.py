from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    """Public marketing pages for search engines."""

    changefreq = 'weekly'
    protocol = 'https'

    def items(self):
        return ['index', 'about', 'register', 'login']

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        if item == 'index':
            return 1.0
        if item == 'about':
            return 0.8
        return 0.5
