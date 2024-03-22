from .models import Event, VerificationAttempt, Setting
import requests
import os
import string
import random
from twilio.rest import Client as TwilioClient
from django.conf import settings
import logging


class VerifyUtil:
    def __init__(self):
        self.session = requests.session()
        self.settings = Setting.objects.first()
        self.twilio_client = TwilioClient(
            self.settings.twilio_account_sid, self.settings.twilio_auth_token
        )
        self.logger = logging.getLogger(name="Verifier")
        self.authorize()

    def authorize(self):
        self.logger.info("Authorizing with Ethos...")
        res = self.session.post(
            url=settings.ETHOS_AUTH_URL,
            headers={"Authorization": f"Bearer {self.settings.ethos_api_key}"},
        )
        self.session.headers = {
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip",
            "Authorization": f"Bearer {res.content.decode()}",
        }

    def get_phone_from_cwid(self, cwid):
        self.logger.info(f"Pulling phone from Banner by CWID {cwid}")
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
        self.logger.debug(response)
        if "data" in response:
            data = response["data"]
            if "persons12" in data:
                person = data["persons12"]
                node = person["edges"][0]["node"]
                phones = node["phones"]
                cell = [
                    phone for phone in phones if phone["type"]["phoneType"] == "mobile"
                ]
                if len(cell) > 0:
                    cell = cell[0]["number"]
                    self.logger.info(f"Mobile phone found: {cell}")
                    return cell
                else:
                    self.logger.error("No mobile phone found for this user.")
                    return None

    def generate_random_passphrase(self):
        return "".join(
            random.choices(
                string.ascii_letters + string.digits, k=settings.PASSPHRASE_LENGTH
            )
        )

    def send_passphrase_to_cell(self, passphrase: str = "", phone_number: str = ""):
        self.logger.info(f"Sending passphrase {passphrase} to user cell {phone_number}")
        try:
            msg_template = self.settings.message_template
            msg_body = msg_template.replace("{{passphrase}}", passphrase)
            message = self.twilio_client.messages.create(
                messaging_service_sid=self.settings.twilio_messaging_service_sid,
                body=msg_body,
                to=phone_number,
            )
            self.logger.info("Message sent")
            self.logger.info(message)
            return message
        except Exception as e:
            self.logger.error("Failed to send")
            self.logger.error(e)
            return None
