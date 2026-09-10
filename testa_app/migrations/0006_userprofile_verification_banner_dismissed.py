from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('testa_app', '0005_pdfdocument_content_text'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='verification_banner_dismissed',
            field=models.BooleanField(
                default=False,
                help_text='Set when the user closes the verify-your-email banner. '
                          'Verification is optional, so the banner stays closed.',
            ),
        ),
    ]
