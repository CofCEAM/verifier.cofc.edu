from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from .models import VerificationAttempt, Setting
from django.conf import settings
from .util import VerifyUtil
from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
import logging
import json

logger = logging.getLogger("views")


class HomeView(View):
    template_name = "index.html"

    def get(self, request):
        if settings.PRODUCTION:
            if request.user.is_authenticated:
                return render(request, template_name=self.template_name, context={})
            else:
                return redirect("web:login")
        else:
            # Development, don't require auth
            return render(request, template_name=self.template_name, context={})


class TwilioCallback(View):
    @csrf_exempt
    def post(self, request):
        """
        As our message is getting delivered,
        Twilio will be making webhook requests
        to our Status Callback URL to let us
        know the delivery status of our message.
        JSON structure =
        {
        "SmsSid": "SMXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        "SmsStatus": "delivered",
        "MessageStatus": "delivered",
        "To": "+15558675310",
        "MessagingServiceSid": "MGXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        "MessageSid": "SMXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        "AccountSid": "XXXXXXXXXXXXXXXXXX",
        "From": "+15017122661",
        "ApiVersion": "2010-04-01"
        }
        """
        try:
            message_delivery_status = request.POST.get("MessageStatus")
            to_phone_number = request.POST.get("To")
            logger.info(
                f"Message delivery callback  (to={to_phone_number}),status={message_delivery_status})"
            )
            # get most recent verification attempt matching this To phone number
            most_recent_attempt = VerificationAttempt.objects.filter(
                phone_number=to_phone_number
            ).order_by("-id")
            if most_recent_attempt.count() > 0:
                most_recent_attempt = most_recent_attempt[0]
                logger.debug(
                    f"Setting delivery status to {message_delivery_status} for "
                    f"most recent verification attempt "
                    f"(id={most_recent_attempt.id}) for number {to_phone_number}"
                )
                most_recent_attempt.message_delivery_status = message_delivery_status
                most_recent_attempt.save()
            status = 200
        except:
            status = 500
        return HttpResponse(status=status)


class GetPhoneFromCWIDView(View, LoginRequiredMixin):
    def post(self, request):
        cwid = request.POST.get("cwid")
        if cwid:
            logger.info(f"Getting phone from CWID: {cwid}")
            if settings.PRODUCTION:
                verifier = request.user
            else:
                verifier = None
            verify_attempt = VerificationAttempt(
                phone_number="", cwid=cwid, verifier=verifier
            )
            verify_attempt.save()
            verify_util = VerifyUtil()
            phone = verify_util.get_phone_from_cwid(cwid=cwid)
            verify_attempt.phone_number = phone
            verify_attempt.save()
            if phone:
                passphrase = verify_util.generate_random_passphrase()
                verify_attempt.passphrase = passphrase
                verify_attempt.save()
                message_template = Setting.objects.first().message_template
                message = message_template.replace("{{passphrase}}", passphrase)
                return render(
                    request,
                    template_name="confirm-send-to-phone.html",
                    context={
                        "phone": phone,
                        "error": False,
                        "message": message,
                        "passphrase": passphrase,
                        "cwid": cwid,
                        "verify_attempt_id": verify_attempt.id,
                    },
                )
            else:
                return render(
                    request, template_name="no-phone-match.html", context={"cwid": cwid}
                )
        return render(request, template_name="index.html", context={})


class SendPassphraseView(View, LoginRequiredMixin):
    def get(self, request):
        cwid = request.GET.get("cwid")
        passphrase = request.GET.get("passphrase")
        phone = request.GET.get("phone")
        verify_attempt_id = request.GET.get("verify_attempt_id")
        logger.info(
            f"Passphrase={passphrase},CWID={cwid},phone={phone},"
            f"verify_attempt_id={verify_attempt_id}"
        )
        if passphrase and phone:
            verify_util = VerifyUtil()
            sent_message = verify_util.send_passphrase_to_cell(
                passphrase=passphrase, phone_number=phone
            )
            if sent_message:
                return render(
                    request,
                    template_name="wait-for-feedback.html",
                    context={
                        "phone": phone,
                        "passphrase": passphrase,
                        "cwid": cwid,
                        "verify_attempt_id": verify_attempt_id,
                    },
                )
            else:
                return render(
                    request,
                    template_name="message-failed-to-send.html",
                    context={"phone": phone},
                )
        else:
            return HttpResponse(
                json.dumps(
                    {"error": "please provide keys phone and message in POST payload"}
                ),
                content_type="application/json",
            )


class Verify(View, LoginRequiredMixin):
    def post(self, request, verify_attempt_id):
        verify_attempt = VerificationAttempt.objects.get(id=verify_attempt_id)
        verified = request.POST.get("verified") == "yes"
        logger.info(f"Verified? {verified}")
        verify_attempt.verification_successful = verified
        verify_attempt.save()
        return render(request, template_name="index.html")


class VerificationLog(View, LoginRequiredMixin):
    def get(self, request):
        attempts = VerificationAttempt.objects.all()
        return render(
            request,
            template_name="verification-log.html",
            context={"verification_attempts": attempts},
        )
