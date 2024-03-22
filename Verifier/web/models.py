from django.db import models
from django.contrib.auth.models import User
from phonenumber_field.modelfields import PhoneNumberField


class Setting(models.Model):
    message_template = models.TextField(
        default="Provide the following passphrase to IT Service desk: {{passphrase}}"
    )
    passphrase_length = models.IntegerField(
        verbose_name="Length of the passphrase to use for verification", default=4
    )
    twilio_account_sid = models.CharField(
        verbose_name="Twilio Account SID (for SMS)", default="", max_length=50
    )
    twilio_auth_token = models.CharField(
        verbose_name="Twilio Auth Token (for SMS)", default="", max_length=50
    )
    twilio_messaging_service_sid = models.CharField(
        verbose_name="Twilio Messaging Service SID (for SMS)", max_length=50
    )
    ethos_api_key = models.CharField(
        "Ethos API Key (for an Ethos Integrate App Registration with persons graphql resource)",
        max_length=50,
    )


# Create your models here.
class Event(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name="User who did action"
    )
    timestamp = models.DateTimeField(verbose_name="Date and time of action")
    action = models.TextField(verbose_name="Action taken by user")


class VerificationAttempt(models.Model):
    verification_successful = models.BooleanField(
        default=False, verbose_name="Was the verification successful?"
    )
    phone_number = PhoneNumberField(null=True, blank=True)
    cwid = models.CharField(max_length=10, null=False, blank=False)
    verifier = models.ForeignKey(User, on_delete=models.PROTECT, blank=True, null=True)
    passphrase = models.CharField(max_length=10, null=True, blank=True)
    message_delivery_status = models.CharField(max_length=20, null=True, blank=True)
