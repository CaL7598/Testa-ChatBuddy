from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('testa_app', '0004_alter_dailyactivity_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='pdfdocument',
            name='content_text',
            field=models.TextField(
                blank=True,
                default='',
                help_text='Extracted text, used to answer questions about this document',
            ),
        ),
    ]
