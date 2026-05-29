from django import template

register = template.Library()


@register.simple_tag
def admin_dashboard_stats():
    from testa_app.admin import get_admin_dashboard_stats

    return get_admin_dashboard_stats()
