from django.views.decorators.csrf import csrf_exempt
from django.views import View
from web.models import VerificationAttempt
from django.http import HttpResponse
import logging

logger = logging.getLogger("django")


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
        logger.info({"payload": request.POST, "action": "TwilioCallback.post"})
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
                logger.info(
                    {
                        "action": "TwilioCallback.post",
                        "message_delivery_status": message_delivery_status,
                        "most_recent_attempt": most_recent_attempt.id,
                        "to_phone_number": to_phone_number,
                    }
                )
                most_recent_attempt.message_delivery_status = message_delivery_status
                most_recent_attempt.save()
            status = 200
        except:
            status = 500
        return HttpResponse(status=status)
