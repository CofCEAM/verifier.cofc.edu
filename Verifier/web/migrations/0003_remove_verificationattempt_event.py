# Generated by Django 4.2.5 on 2023-09-07 02:20

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0002_verificationattempt_passphrase"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="verificationattempt",
            name="event",
        ),
    ]
