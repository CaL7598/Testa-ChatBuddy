"""Smoke-test admin changelist URLs (Render Shell: python manage.py test_admin_pages)."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.test import Client


class Command(BaseCommand):
    help = 'GET admin changelist pages as superuser; prints status codes.'

    def handle(self, *args, **options):
        user = get_user_model().objects.filter(is_superuser=True).first()
        if not user:
            self.stderr.write(self.style.ERROR('No superuser found.'))
            return

        client = Client()
        client.force_login(user)
        paths = [
            '/admin/testa_app/questionanswer/',
            '/admin/testa_app/pdfdocument/',
            '/admin/testa_app/dailyactivity/',
            '/admin/testa_app/bookmark/',
            '/admin/testa_app/exporthistory/',
            '/admin/testa_app/quizattempt/',
            '/admin/testa_app/flashcard/',
        ]
        for path in paths:
            response = client.get(path)
            line = f'{path} -> {response.status_code}'
            if response.status_code >= 400:
                self.stderr.write(self.style.ERROR(line))
            else:
                self.stdout.write(self.style.SUCCESS(line))
