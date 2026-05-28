"""Transactional email via SendGrid (SMTP) with HTML templates."""
from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

logger = logging.getLogger(__name__)


def get_site_url(request=None) -> str:
    configured = getattr(settings, 'SITE_URL', '').strip()
    if configured:
        return configured.rstrip('/')
    if request is not None:
        scheme = 'https' if request.is_secure() else 'http'
        host = request.get_host()
        return f'{scheme}://{host}'
    return 'http://127.0.0.1:8000'


def build_email_context(request=None, user=None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    ctx: dict[str, Any] = {
        'site_name': getattr(settings, 'SITE_NAME', 'Testa StudyBuddy'),
        'site_url': get_site_url(request),
        'support_email': getattr(settings, 'SUPPORT_EMAIL', settings.DEFAULT_FROM_EMAIL),
    }
    if user is not None:
        ctx['user'] = user
        ctx['username'] = user.get_username()
        ctx['email'] = user.email
    if extra:
        ctx.update(extra)
    return ctx


def send_templated_email(
    to_email: str,
    subject: str,
    text_template: str,
    html_template: str,
    context: dict[str, Any],
    *,
    request=None,
    user=None,
) -> bool:
    if not to_email:
        logger.warning('send_templated_email skipped: empty recipient')
        return False

    ctx = build_email_context(request, user, context)
    text_body = render_to_string(text_template, ctx).strip()
    html_body = render_to_string(html_template, ctx)

    try:
        message = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
        )
        message.attach_alternative(html_body, 'text/html')
        message.send(fail_silently=False)
        logger.info('Email sent to %s: %s', to_email, subject)
        return True
    except Exception:
        logger.exception('Failed to send email to %s: %s', to_email, subject)
        raise


def _verification_link(request, user) -> tuple[str, str, str]:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    link = f"{get_site_url(request)}/verify-email/{uid}/{token}/"
    return uid, token, link


def send_welcome_email(user, request=None) -> bool:
    uid, token, verify_link = _verification_link(request, user)
    return send_templated_email(
        user.email,
        f'Welcome to {settings.SITE_NAME}! 🎓',
        'testa_app/emails/welcome.txt',
        'testa_app/emails/welcome.html',
        {'verify_link': verify_link, 'uid': uid, 'token': token},
        request=request,
        user=user,
    )


def send_verification_email(user, request=None) -> bool:
    uid, token, verify_link = _verification_link(request, user)
    return send_templated_email(
        user.email,
        f'Verify your email — {settings.SITE_NAME}',
        'testa_app/emails/verify_email.txt',
        'testa_app/emails/verify_email.html',
        {'verify_link': verify_link, 'uid': uid, 'token': token},
        request=request,
        user=user,
    )

