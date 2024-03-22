import yaml
from requests_oauthlib import OAuth2Session
import os
import time
import logging

logger = logging.getLogger(__name__)
# This is necessary for testing with non-HTTPS localhost
# Remove this if deploying to production
# os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# This is necessary because Azure does not guarantee
# to return scopes in the same case and order as requested
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"
os.environ["OAUTHLIB_IGNORE_SCOPE_CHANGE"] = "1"

# Load the oauth_settings.yml file
stream = open("oauth_settings.yml", "r")
settings = yaml.load(stream, yaml.SafeLoader)
authorize_url = "{0}{1}".format(settings["authority"], settings["authorize_endpoint"])
token_url = "{0}{1}".format(settings["authority"], settings["token_endpoint"])


graph_url = "https://graph.microsoft.com"


def get_user(token):
    graph_client = OAuth2Session(token=token)
    # Send GET to /me
    user = graph_client.get(f"{graph_url}/v1.0/me")
    # Return the JSON result
    return user.json(), graph_client


def user_in_group(group_id, graph_client):
    logger.debug(f"Checking if user in group {group_id}")
    response = graph_client.get(
        f"{graph_url}/v1.0/me/memberOf?$filter=id eq '{group_id}'"
    ).json()
    return (
        "error" not in response and "value" in response and len(response["value"]) > 0
    )


def user_has_access_to_service_principal(user_id, graph_client):
    service_principal_id = settings["service_principal_id"]
    url = f"{graph_url}/beta/servicePrincipals/{service_principal_id}/appRoleAssignedTo"
    response = graph_client.get(url)
    data = response.json()
    logger.debug(f"Response from {url}")
    logger.debug(data)
    if "value" in data:
        role_assignments = data["value"]
        for ra in role_assignments:
            principal_type = ra["principalType"]
            principal_display_name = ra["principalDisplayName"]
            principal_id = ra["principalId"]
            if principal_type == "User" and user_id == principal_id:
                return True
            elif principal_type == "Group" and user_in_group(
                group_id=principal_id, graph_client=graph_client
            ):
                return True
    # went through all assignments, found no match for this user
    return False


# Method to generate a sign-in url
def get_sign_in_url():
    # Initialize the OAuth client
    aad_auth = OAuth2Session(
        settings["app_id"], scope=settings["scopes"], redirect_uri=settings["redirect"]
    )

    sign_in_url, state = aad_auth.authorization_url(authorize_url, prompt="login")

    return sign_in_url, state


# Method to exchange auth code for access token
def get_token_from_code(callback_url, expected_state):
    # Initialize the OAuth client
    logger.debug(
        f"Getting token from code with callback url {callback_url} and expected state {expected_state}"
    )
    aad_auth = OAuth2Session(
        settings["app_id"],
        state=expected_state,
        scope=settings["scopes"],
        redirect_uri=settings["redirect"],
    )

    token = aad_auth.fetch_token(
        token_url,
        client_secret=settings["app_secret"],
        authorization_response=callback_url,
    )
    logger.debug(f"Returning token {token}")
    return token


def store_token(request, token):
    request.session["oauth_token"] = token


def store_user(request, user):
    request.session["user"] = {
        "is_authenticated": True,
        "name": user["displayName"],
        "email": user["mail"] if (user["mail"] != None) else user["userPrincipalName"],
    }


def get_token(request):
    token = request.session["oauth_token"]
    if token != None:
        # Check expiration
        now = time.time()
        # Subtract 5 minutes from expiration to account for clock skew
        expire_time = token["expires_at"] - 300
        if now >= expire_time:
            # Refresh the token
            aad_auth = OAuth2Session(
                settings["app_id"],
                token=token,
                scope=settings["scopes"],
                redirect_uri=settings["redirect"],
            )

            refresh_params = {
                "client_id": settings["app_id"],
                "client_secret": settings["app_secret"],
            }
            new_token = aad_auth.refresh_token(token_url, **refresh_params)

            # Save new token
            store_token(request, new_token)

            # Return new access token
            return new_token

        else:
            # Token still valid, just return it
            return token


def remove_user_and_token(request):
    if "oauth_token" in request.session:
        del request.session["oauth_token"]

    if "user" in request.session:
        del request.session["user"]
