# Merge parallel 0002 branches: analytics models + UserProfile

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('testa_app', '0002_topicmastery_useranalytics_pdfdocument_course_and_more'),
        ('testa_app', '0002_userprofile'),
    ]

    operations = []
