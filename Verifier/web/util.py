import requests
import string
import random
import time
import logging

from twilio.rest import Client as TwilioClient
from django.conf import settings
from .models import *
from requests_oauthlib import OAuth2Session


logger = logging.getLogger("django")

graph_url = "https://graph.microsoft.com"


class VerifyUtil:
    def __init__(self):
        self.session = requests.session()
        self.twilio_client = TwilioClient(
            settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN
        )
        self.authorize()

    def authorize(self):
        logger.info(
            {
                "action": "VerifyUtil.authorize",
                "url": settings.ETHOS_AUTH_URL,
            }
        )
        res = self.session.post(
            url=settings.ETHOS_AUTH_URL,
            headers={"Authorization": f"Bearer {settings.ETHOS_API_KEY}"},
        )
        self.session.headers = {
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip",
            "Authorization": f"Bearer {res.content.decode()}",
        }

    def get_phone_from_cwid(self, cwid):
        logger.info({"action": "VerifyUtil.get_phone_from_cwid", "cwid": cwid})
        body = (
            " query {"
            "     persons12("
            "         filter: {"
            "             credentials: {"
            "                AND:  {"
            "                    type: {EQ: bannerId}, "
            f'                    value: {{EQ: "{cwid}"}}'
            "                    }"
            "                }"
            "         }"
            "     ) {"
            "         edges {"
            "             node {"
            "                 phones {type {phoneType}, number}"
            "             }"
            "         }"
            "     }"
            "  } "
        )
        response = self.session.post(
            url=settings.ETHOS_GRAPHQL_URL, json={"query": body}
        )
        response = response.json()
        logger.info(
            {
                "action": "VerifyUtil.get_phone_from_cwid",
                "response_from_ethos": response,
            }
        )
        if "data" in response:
            data = response["data"]
            if "persons12" in data:
                person = data["persons12"]
                if "edges" not in person or len(person["edges"]) == 0:
                    logger.error("No edges found for this user.")
                    return None
                first_edge = person["edges"][0]
                if "node" not in first_edge:
                    logger.error("No node found for this user.")
                    return None
                node = first_edge["node"]
                if "phones" not in node:
                    logger.error("No phones found for this user.")
                    return None
                phones = node["phones"]
                cell = [
                    phone for phone in phones if phone["type"]["phoneType"] == "mobile"
                ]
                if len(cell) > 0:
                    cell = cell[0]["number"]
                    logger.info(f"Mobile phone found: {cell}")
                    return cell
                else:
                    logger.error("No mobile phone found for this user.")
                    return None

    def generate_random_passphrase(self):
        logger.info({"action": "VerifyUtil.generate_random_passphrase"})
        return "".join(
            random.choices(
                string.ascii_letters + string.digits, k=settings.PASSPHRASE_LENGTH
            )
        )

    def send_passphrase_to_cell(self, passphrase: str = "", phone_number: str = ""):
        logger.info(
            {
                "action": "VerifyUtil.send_passphrase_to_cell",
                "passphrase": passphrase,
                "phone_number": phone_number,
            }
        )
        try:
            msg_body = settings.MESSAGE_TEMPLATE.replace("{{passphrase}}", passphrase)
            message = self.twilio_client.messages.create(
                messaging_service_sid=settings.TWILIO_MESSAGING_SERVICE_SID,
                body=msg_body,
                to=phone_number,
            )
            logger.info(
                {
                    "action": "VerifyUtil.send_passphrase_to_cell",
                    "message_sent": message,
                }
            )
            return message
        except Exception as e:
            logger.error(
                {
                    "action": "VerifyUtil.send_passphrase_to_cell",
                    "error": str(e),
                }
            )
            return None


### AUTH UTILS
def get_user(token):
    logger.info({"action": "get_user"})
    graph_client = OAuth2Session(token=token)
    user = graph_client.get("{0}/me".format("https://graph.microsoft.com/v1.0"))
    logger.debug({"user": user.json()})
    return user.json(), graph_client


# Method to generate a sign-in url
def get_sign_in_url():
    # Initialize the OAuth client
    aad_auth = OAuth2Session(
        settings.MICROSOFT_AUTH_CLIENT_ID,
        scope=settings.MICROSOFT_AUTH_SCOPES,
        redirect_uri=settings.MICROSOFT_AUTH_REDIRECT_URI,
    )

    sign_in_url, state = aad_auth.authorization_url(
        settings.MICROSOFT_AUTH_AUTHORIZE_ENDPOINT, prompt="login"
    )

    return sign_in_url, state


# Method to exchange auth code for access token
def get_token_from_code(callback_url, expected_state):
    # Initialize the OAuth client
    logger.debug(
        f"Getting token from code with callback url {callback_url} and expected state {expected_state}"
    )
    aad_auth = OAuth2Session(
        settings.MICROSOFT_AUTH_CLIENT_ID,
        state=expected_state,
        scope=settings.MICROSOFT_AUTH_SCOPES,
        redirect_uri=settings.MICROSOFT_AUTH_REDIRECT_URI,
    )

    token = aad_auth.fetch_token(
        settings.MICROSOFT_AUTH_TOKEN_ENDPOINT,
        client_secret=settings.MICROSOFT_AUTH_CLIENT_SECRET,
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
                settings.MICROSOFT_AUTH_CLIENT_ID,
                token=token,
                scope=settings.MICROSOFT_AUTH_SCOPES,
                redirect_uri=settings.MICROSOFT_AUTH_REDIRECT_URI,
            )

            refresh_params = {
                "client_id": settings.MICROSOFT_AUTH_CLIENT_ID,
                "client_secret": settings.MICROSOFT_AUTH_CLIENT_SECRET,
            }
            new_token = aad_auth.refresh_token(
                settings.MICROSOFT_AUTH_TOKEN_ENDPOINT, **refresh_params
            )

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


def user_in_group(group_id, graph_client):
    logger.info(
        {
            "action": "user_in_group",
            "group_id": group_id,
        }
    )
    logger.debug(f"Checking if user in group {group_id}")
    response = graph_client.get(
        f"{graph_url}/v1.0/me/memberOf?$filter=id eq '{group_id}'"
    ).json()
    return (
        "error" not in response and "value" in response and len(response["value"]) > 0
    )


def user_has_access_to_service_principal(user_id, graph_client):
    """Determine whether user has access to service principal (enterprise app) corresponding to this app"""
    logger.info(
        {
            "action": "user_has_access_to_service_principal",
            "user_id": user_id,
        }
    )
    url = f"{graph_url}/beta/servicePrincipals/{settings.MICROSOFT_AUTH_SERVICE_PRINCIPAL_ID}/appRoleAssignedTo"
    response = graph_client.get(url)
    data = response.json()
    logger.info(
        {"action": "user_has_access_to_service_principal", "graph_response": data}
    )
    if "value" in data:
        role_assignments = data["value"]
        for ra in role_assignments:
            principal_type = ra["principalType"]
            principal_display_name = ra["principalDisplayName"]
            principal_id = ra["principalId"]
            if principal_type == "User" and user_id == principal_id:
                logger.info(
                    {
                        "action": "user_has_access_to_service_principal",
                        "result": True,
                        "message": f"User has direct access",
                        "principal_type": principal_type,
                        "principal_display_name": principal_display_name,
                        "principal_id": principal_id,
                    }
                )
                return True
            elif principal_type == "Group" and user_in_group(
                group_id=principal_id, graph_client=graph_client
            ):
                logger.info(
                    {
                        "action": "user_has_access_to_service_principal",
                        "result": True,
                        "message": "User in group with access",
                        "principal_type": principal_type,
                        "principal_display_name": principal_display_name,
                        "principal_id": principal_id,
                    }
                )
                return True
    # went through all assignments, found no match for this user
    logger.error(
        {
            "action": "user_has_access_to_service_principal",
            "result": False,
            "message": "User has no access",
        }
    )
    return False
