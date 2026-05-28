"""Authentication views: password reset, email verification."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import (
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode

from .email_service import get_site_url, send_verification_email
from .models import UserProfile

User = get_user_model()


class TestaPasswordResetView(PasswordResetView):
    template_name = 'testa_app/auth/forgot_password.html'
    email_template_name = 'testa_app/emails/password_reset.txt'
    html_email_template_name = 'testa_app/emails/password_reset.html'
    subject_template_name = 'testa_app/emails/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')

    def form_valid(self, form):
        from django.conf import settings

        self.extra_email_context = {
            'site_url': get_site_url(self.request),
            'site_name': settings.SITE_NAME,
        }
        return super().form_valid(form)


class TestaPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'testa_app/auth/password_reset_done.html'


class TestaPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'testa_app/auth/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')


class TestaPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'testa_app/auth/password_reset_complete.html'


def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.mark_verified()
        messages.success(
            request,
            'Your email is verified. You are all set to use Testa StudyBuddy!',
        )
        if request.user.is_authenticated:
            return redirect('question_answer')
        return redirect('login')

    messages.error(
        request,
        'This verification link is invalid or has expired. You can request a new one below.',
    )
    return redirect('resend_verification')


def resend_verification(request):
    if request.method == 'POST':
        email = (request.POST.get('email') or '').strip()
        if not email:
            messages.error(request, 'Please enter your email address.')
        else:
            users = User.objects.filter(email__iexact=email)
            if users.exists():
                for user in users:
                    profile, _ = UserProfile.objects.get_or_create(user=user)
                    if not profile.email_verified:
                        try:
                            send_verification_email(user, request)
                        except Exception:
                            messages.error(
                                request,
                                'We could not send the email right now. Please try again later.',
                            )
                            return render(request, 'testa_app/auth/resend_verification.html')
            messages.success(
                request,
                'If an account exists with that email and is not yet verified, '
                'we sent a new verification link.',
            )
            return redirect('login')
    elif request.user.is_authenticated:
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        if not profile.email_verified:
            try:
                send_verification_email(request.user, request)
                messages.success(request, 'Verification email sent. Check your inbox.')
            except Exception:
                messages.error(request, 'Could not send email. Please try again later.')
            return redirect('question_answer')

    return render(request, 'testa_app/auth/resend_verification.html', {
        'site_url': get_site_url(request),
    })
