from web.auth import auth
import web.views as views
from django.urls import path

app_name = "web"
urlpatterns = [
    path(
        "get-phone-from-cwid",
        views.GetPhoneFromCWIDView.as_view(),
        name="get-phone-from-cwid",
    ),
    path("twilio-callback", views.TwilioCallback.as_view(), name="twilio-callback"),
    path("send-passphrase", views.SendPassphraseView.as_view(), name="send-passphrase"),
    path("verify/<slug:verify_attempt_id>", views.Verify.as_view(), name="verify"),
    path("verification-log", views.VerificationLog.as_view(), name="verification-log"),
    # Authentication
    path("login/", auth.sign_in, name="login"),
    path("logout/", auth.signout, name="logout"),
    # Add a callback url pattern that matches the Azure Registered App's Redirect URI
    path("custom-microsoft-callback/", auth.microsoft_auth_callback),
    path("", views.HomeView.as_view(), name="home"),
]
