import json
import decimal
from os.path import join
import re
from datetime import datetime, date, time
import requests
import xero.utils
from singer.utils import strftime
import six
import pytz
from .credentials import build_oauth
from xero.exceptions import XeroUnauthorized
from requests_oauthlib import OAuth1
from oauthlib.oauth1 import SIGNATURE_RSA, SIGNATURE_TYPE_AUTH_HEADER

BASE_URL = "https://api.xero.com/api.xro/2.0"


def _json_load_object_hook(_dict):
    """Hook for json.parse(...) to parse Xero date formats."""
    # This was taken from the pyxero library and modified
    # to format the dates according to RFC3339
    for key, value in _dict.items():
        if isinstance(value, six.string_types):
            value = xero.utils.parse_date(value)
            if value:
                if type(value) == date:
                    value = datetime.combine(value, time.min)
                value = value.replace(tzinfo=pytz.UTC)
                _dict[key] = strftime(value)
    return _dict


class XeroClient(object):
    def __init__(self, config):
        self.session = requests.Session()
        self.oauth = build_oauth(config)
        self.user_agent = config.get("user_agent")

    def update_credentials(self, new_config):
        self.oauth = build_oauth(new_config)

    def filter(self, tap_stream_id, *args, since=None, **params):
        xero_resource_name = tap_stream_id.title().replace("_", "")
        url = join(BASE_URL, xero_resource_name)
        headers = {"Accept": "application/json"}
        if self.user_agent:
            headers["User-Agent"] = self.user_agent
        if since:
            headers["If-Modified-Since"] = since
        request = requests.Request("GET", url, auth=self.oauth, headers=headers, params=params)
        response = self.session.send(request.prepare())
        if response.status_code == 401:
            raise XeroUnauthorized(response)
        response.raise_for_status()
        response_meta = json.loads(response.text, object_hook=_json_load_object_hook, parse_float=decimal.Decimal)
        response_body = response_meta.pop(xero_resource_name)
        return response_body


from xero import Xero
from xero.auth import PrivateCredentials


class XeroPrivateClient(object):
    def __init__(self, config):

        self.user_agent = config.get("user_agent")
        self.session = requests.Session()

        rsa_key_path = config.get("rsa_key")
        consumer_key = config.get("consumer_key")

        with open(rsa_key_path) as keyfile:
            rsa_key = keyfile.read()

        credentials = PrivateCredentials(consumer_key, rsa_key)
        self.oauth = OAuth1(
            consumer_key, resource_owner_key=consumer_key, rsa_key=rsa_key, signature_method=SIGNATURE_RSA, signature_type=SIGNATURE_TYPE_AUTH_HEADER
        )

    def update_credentials(self, new_config):
        # We don't need to do anything here, as we have all the auth stuff we need
        # because we are a private app.
        pass

    def filter(self, tap_stream_id, *args, since=None, **params):
        xero_resource_name = tap_stream_id.title().replace("_", "")
        url = join(BASE_URL, xero_resource_name)
        headers = {"Accept": "application/json"}
        if self.user_agent:
            headers["User-Agent"] = self.user_agent
        if since:
            headers["If-Modified-Since"] = since
        request = requests.Request("GET", url, auth=self.oauth, headers=headers, params=params)
        response = self.session.send(request.prepare())
        if response.status_code == 401:
            raise XeroUnauthorized(response)
        response.raise_for_status()
        response_meta = json.loads(response.text, object_hook=_json_load_object_hook, parse_float=decimal.Decimal)
        response_body = response_meta.pop(xero_resource_name)
        return response_body
