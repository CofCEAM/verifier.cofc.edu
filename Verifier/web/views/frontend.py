from django.shortcuts import render, redirect
from django.views import View
from django.conf import settings
from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin

from web.models import VerificationAttempt
from web.util import VerifyUtil

import logging
import json

logger = logging.getLogger("django")


class HomeView(View):
    template_name = "index.html"

    def get(self, request):
        logger.info({"action": "HomeView.get", "user": request.user.username})
        if request.user.is_authenticated:
            return render(request, template_name=self.template_name, context={})
        else:
            return redirect("web:login")


class GetPhoneFromCWIDView(View, LoginRequiredMixin):
    def post(self, request):
        logger.info(
            {
                "action": "GetPhoneFromCWIDView.post",
                "user": request.user.username,
                "payload": request.POST,
            }
        )
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
                message = settings.MESSAGE_TEMPLATE.replace(
                    "{{passphrase}}", passphrase
                )
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
        logger.info(
            {
                "action": "SendPassphraseView.get",
                "user": request.user.username,
                "query_params": request.GET,
            }
        )
        cwid = request.GET.get("cwid")
        passphrase = request.GET.get("passphrase")
        phone = request.GET.get("phone")
        verify_attempt_id = request.GET.get("verify_attempt_id")
        logger.info(
            {
                "cwid": cwid,
                "passphrase": passphrase,
                "phone": phone,
                "verify_attempt_id": verify_attempt_id,
            }
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
            logger.error(
                {"error": "please provide keys phone and passphrase in GET payload"}
            )
            return HttpResponse(
                json.dumps(
                    {"error": "please provide keys phone and message in POST payload"}
                ),
                content_type="application/json",
            )


class Verify(View, LoginRequiredMixin):
    def post(self, request, verify_attempt_id):
        logger.info(
            {
                "action": "Verify.post",
                "user": request.user.username,
                "payload": request.POST,
            }
        )
        verify_attempt = VerificationAttempt.objects.get(id=verify_attempt_id)
        verified = request.POST.get("verified") == "yes"
        logger.info(f"Verified? {verified}")
        verify_attempt.verification_successful = verified
        verify_attempt.save()
        return render(request, template_name="index.html")


class VerificationLog(View, LoginRequiredMixin):
    def get(self, request):
        logger.info(
            {
                "action": "VerificationLog.get",
                "user": request.user.username,
            }
        )
        attempts = VerificationAttempt.objects.all()
        return render(
            request,
            template_name="verification-log.html",
            context={"verification_attempts": attempts},
        )
