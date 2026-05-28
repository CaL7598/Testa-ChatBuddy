_DEFAULT_DESCRIPTION = (
    'Testa StudyBuddy is an AI-powered learning platform for students — '
    'ask questions from your course materials, flashcards, quizzes, and study analytics.'
)


def seo(request):
    from django.conf import settings

    site_url = getattr(settings, 'SITE_URL', '').strip().rstrip('/')
    if site_url:
        canonical_url = f'{site_url}{request.path}'
    else:
        canonical_url = request.build_absolute_uri(request.path)

    return {
        'site_url': site_url,
        'site_name': getattr(settings, 'SITE_NAME', 'Testa StudyBuddy'),
        'seo_description': getattr(settings, 'SEO_DESCRIPTION', _DEFAULT_DESCRIPTION),
        'google_site_verification': getattr(settings, 'GOOGLE_SITE_VERIFICATION', ''),
        'canonical_url': canonical_url,
    }


def email_verification_banner(request):
    if not request.user.is_authenticated:
        return {}
    from .models import UserProfile

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if profile.email_verified:
        return {}
    return {'show_email_verification_banner': True}
