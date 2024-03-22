from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
import logging
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from .auth_helper import (
    get_sign_in_url,
    get_token_from_code,
    remove_user_and_token,
    get_user,
    user_has_access_to_service_principal,
)

logger = logging.getLogger(__name__)


def signout(request):
    logout(request)
    remove_user_and_token(request)
    return redirect("/")


def sign_in(request):
    # Get the sign-in URL
    logger.debug("Generating a new state at the /login/ page.")
    sign_in_url, state = get_sign_in_url()
    # Save the expected state so we can validate in the callback
    request.session["auth_state"] = state.strip()
    logger.debug(f"State is now: {request.session['auth_state']}")
    # Redirect to the Azure sign-in page
    return redirect(sign_in_url)


def microsoft_auth_callback(request):
    """Microsoft will POST to https://verifier.cofc.edu/custom-microsoft-callback/ when a user logs in through Microsoft"""
    expected_state = request.session.pop("auth_state", "")
    logger.debug(f"at the callback url, the expected state is {expected_state}")
    # Make the token request
    logger.debug(f"callback url (current location) is {request.build_absolute_uri()}")
    token = get_token_from_code(
        callback_url=request.build_absolute_uri().replace("http:", "https:"),
        expected_state=expected_state,
    )
    # Get the user's profile
    user, graph_client = get_user(token)
    logger.debug("User: ")
    logger.debug(f"{user}")
    # Get user info
    # user attribute like displayName,surname,mail etc. are defined by the
    # institute incase you are using single-tenant. You can get these
    # attribute by exploring Microsoft graph-explorer.

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
    if len(User.objects.filter(username=username)) > 0 and authenticated_user is None:
        # Then update their password to be constant password=password
        logger.debug(
            "User exists with a different local password than constant password; resetting to constant pass"
        )
        user = User.objects.filter(username=username)[0]
        user.set_password(password)
        user.save()

    # elif user does not exist yet locally
    elif len(User.objects.filter(username=username)) == 0:
        logger.debug(
            "User doesn't exist yet, checking if authorized to access service principal (enterprise app)..."
        )

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
