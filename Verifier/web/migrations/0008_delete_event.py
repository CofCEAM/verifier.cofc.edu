# Generated by Django 5.0.3 on 2025-03-17 18:14

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0007_alter_verificationattempt_timestamp'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Event',
        ),
    ]
