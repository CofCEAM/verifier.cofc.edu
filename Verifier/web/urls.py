from web.views import *
from django.urls import path

app_name = "web"
urlpatterns = [
    path(
        "get-phone-from-cwid",
        GetPhoneFromCWIDView.as_view(),
        name="get-phone-from-cwid",
    ),
    path("twilio-callback", TwilioCallback.as_view(), name="twilio-callback"),
    path("send-passphrase", SendPassphraseView.as_view(), name="send-passphrase"),
    path("wait-for-feedback", WaitForFeedback.as_view(), name="wait-for-feedback"),
    path(
        "message-failed-to-send",
        MessageFailedToSend.as_view(),
        name="message-failed-to-send",
    ),
    path("verify/<slug:verify_attempt_id>", Verify.as_view(), name="verify"),
    path("verification-log", VerificationLog.as_view(), name="verification-log"),
    # Authentication
    path("login/", SignInView.as_view(), name="login"),
    path("logout/", SignOutView.as_view(), name="logout"),
    # Add a callback url pattern that matches the Azure Registered App's Redirect URI
    path(
        "custom-microsoft-callback/",
        MicrosoftAuthCallbackView.as_view(),
        name="custom-microsoft-callback",
    ),
    path("", HomeView.as_view(), name="home"),
]
