from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from django.views import View
from django.shortcuts import redirect
from django.http import HttpResponseForbidden
from django.contrib.auth.mixins import LoginRequiredMixin
import logging
from web.util import (
    get_sign_in_url,
    get_token_from_code,
    remove_user_and_token,
    get_user,
    user_has_access_to_service_principal,
)

logger = logging.getLogger("django")


class SignOutView(View, LoginRequiredMixin):
    def get(self, request):
        logger.info(
            {
                "action": "SignOutView.get",
            }
        )
        logout(request)
        remove_user_and_token(request)
        return redirect("/")


class SignInView(View):
    def get(self, request):
        logger.info(
            {
                "action": "SignInView.get",
            }
        )
        # Get the sign-in URL
        logger.debug("Generating a new state at the /login/ page.")
        sign_in_url, state = get_sign_in_url()
        # Save the expected state so we can validate in the callback
        request.session["auth_state"] = state.strip()
        logger.debug(f"State is now: {request.session['auth_state']}")
        # Redirect to the Azure sign-in page
        return redirect(sign_in_url)


class MicrosoftAuthCallbackView(View):
    def get(self, request):
        logger.info(
            {
                "action": "MicrosoftAuthCallbackView.get",
            }
        )
        expected_state = request.session.pop("auth_state", "")
        token = get_token_from_code(
            callback_url=request.build_absolute_uri().replace("http:", "https:"),
            expected_state=expected_state,
        )
        # Get the user's profile
        user, graph_client = get_user(token)

        username = user["mail"]
        user_id = user["id"]
        password = "thisisanirrelevantpassword"
        email = user["mail"]

        # user signed in with microsoft.

        # only proceed if user has access to corresponding enterprise app (service principal)
        if not user_has_access_to_service_principal(
            user_id=user_id, graph_client=graph_client
        ):
            return HttpResponseForbidden()

        authenticated_user = authenticate(username=username, password=password)

        # If the user exists but with a different local password
        if (
            len(User.objects.filter(username=username)) > 0
            and authenticated_user is None
        ):
            # Then update their password to be constant password=password
            logger.debug(
                "User exists with a different local password than constant password; resetting to constant pass"
            )
            user = User.objects.filter(username=username)[0]
            user.set_password(password)
            user.save()

        # elif user does not exist yet locally
        elif len(User.objects.filter(username=username)) == 0:
            logger.debug("User doesn't exist yet, creating user...")
            # if user does not exist then create a new user
            new_django_user = User.objects.create_user(username, email, password)
            new_django_user.first_name = user["givenName"]
            new_django_user.last_name = user["surname"]
            new_django_user.save()

        # user was properly authenticated
        elif authenticated_user is not None:
            pass

        logger.debug(
            f"User now exists with username {username} and password {password}, so authenticate them"
        )
        user = authenticate(username=username, password=password)

        if user is not None:
            logger.debug("User is not none. login(request,user) and send home")
            login(request, user)
            if request.session.get("redirect_after_authentication", None):
                return redirect(request.session.get("redirect_after_authentication"))
            return redirect("/")
        else:
            logger.debug("User is None. Send back to /login/")
            return redirect("/login/")
