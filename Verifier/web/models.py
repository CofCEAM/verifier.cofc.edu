from django.db import models
from django.contrib.auth.models import User
from phonenumber_field.modelfields import PhoneNumberField


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
