"""Populate PDFDocument.content_text for documents uploaded before the field existed.

Documents without stored text cannot be searched when answering questions, so
run this once after migrating:

    python manage.py backfill_document_text
"""
from django.core.management.base import BaseCommand

from testa_app.models import PDFDocument
from testa_app.document_retrieval import store_document_text


class Command(BaseCommand):
    help = "Extract and store text for documents that have none."

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help="Re-extract text even for documents that already have it.",
        )

    def handle(self, *args, **options):
        queryset = PDFDocument.objects.all().order_by('pk')
        if not options['force']:
            queryset = queryset.filter(content_text='')

        total = queryset.count()
        if not total:
            self.stdout.write(self.style.SUCCESS("Every document already has stored text."))
            return

        self.stdout.write(f"Extracting text for {total} document(s)...")
        done = 0
        failed = []

        for document in queryset.iterator():
            label = document.title or str(document.pk)
            text = store_document_text(document)
            if text:
                done += 1
                self.stdout.write(f"  ok    {label} ({len(text)} chars)")
            else:
                failed.append(label)
                self.stdout.write(self.style.WARNING(f"  skip  {label} (no readable text)"))

        self.stdout.write(self.style.SUCCESS(f"\nStored text for {done}/{total} document(s)."))
        if failed:
            self.stdout.write(self.style.WARNING(
                "Could not extract: " + ", ".join(failed) +
                "\nThese are usually scanned/image-only files, or files missing from disk "
                "(Render's free tier does not persist uploads across restarts)."
            ))
