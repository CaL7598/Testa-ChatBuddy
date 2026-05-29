"""Test OpenRouter API key (run on Render Shell: python manage.py check_openrouter)."""

from django.core.management.base import BaseCommand

from testa_app.bytez_client import BytezClient, _resolve_openrouter_api_key


class Command(BaseCommand):
    help = "Verify OPENROUTER_API_KEY works with OpenRouter (does not print the full key)."

    def handle(self, *args, **options):
        key = _resolve_openrouter_api_key()
        if not key:
            self.stderr.write(self.style.ERROR("OPENROUTER_API_KEY is missing."))
            return

        preview = f"{key[:10]}...{key[-4:]}" if len(key) > 16 else "(too short)"
        self.stdout.write(f"Key loaded: {preview} (length {len(key)})")

        try:
            client = BytezClient(api_key=key)
            reply = client.chat(
                [{"role": "user", "content": "Reply with exactly: OK"}],
                max_length=16,
                temperature=0,
            )
            self.stdout.write(self.style.SUCCESS(f"OpenRouter OK. Model reply: {reply.strip()[:80]}"))
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"OpenRouter failed: {exc}"))
            if "401" in str(exc) or "User not found" in str(exc):
                self.stderr.write(
                    "This key is invalid or was deleted. Create a new key at "
                    "https://openrouter.ai/keys and update Render Environment."
                )
