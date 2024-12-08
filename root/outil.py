import base64
import json
import random
import time
import string

import requests
from django.core.files.base import ContentFile
from django.urls import reverse

from .code_paiement import paiement_login, paiement_password

MOYEN_PAIEMENT = [
    ("Orange Money", "Orange Money"),
    ("Moov Money", "Moov Money"),
    ("Sama Money", "Sama Money"),
    ("Carte Visa", "Carte Visa"),
]


def base64_to_image(data):
    try:
        format, imgstr = data.split(';base64,')
        ext = format.split('/')[-1]
    except:
        return None

    return ContentFile(base64.b64decode(imgstr),
                       name=f"{random.randint(0, 18000)}/{time.time()}." + ext)


def get_order_id(k=32):
    return "".join(random.choices(string.ascii_letters + string.digits, k=32))


def verifier_numero(numero):
    if len(numero) != 8:
        return False
    for c in numero:
        if c not in string.digits:
            return False
    return True


def paiement_orange(montant, numero, order_id, notify_url):
    data = {

        "login": paiement_login,
        "password": paiement_password,
        "telephone": numero,
        "montant": montant,
        "orderId": order_id,
        "notify_url": notify_url

    }

    resp = requests.post("https://ngsystem.net/sms/rest/smsService/orange/pay",
                         data=json.dumps(data))
    if resp.status_code == 200:
        return resp.json()
    else:
        return False


def paiement_moov(montant, numero, order_id, description, remarks, notify_url):
    data = {
        "password": paiement_password,
        "login": paiement_login,
        "telephone": numero,
        "montant": montant,
        "remarks": remarks,
        "description": description,
        "orderId": order_id,
        "type": "PAY",
        "callback_url": notify_url
    }

    resp = requests.post("https://ngsystem.net/sms/rest/smsService/moov/transaction",
                         data=json.dumps(data))

    if resp.status_code == 200:
        return resp.json()
    else:
        return False


def sama_pay(montant, order_id, numero, description, notify_url):
    data = {
        "login": paiement_login,
        "password": paiement_password,
        "montant": montant,
        "orderId": order_id,
        "callback_url": notify_url,
        "phone_client": numero,
        "description": description

    }
    # TODO notify_url

    resp = requests.post("https://ngsystem.net/sms/rest/smsService/sama/pay",
                         data=json.dumps(data))
    if resp.status_code == 200:
        return resp.json()
    else:
        return False


def stripe_pay(montant, name, description, return_url, order_id, notify_url):
    data = {
        "password": paiement_password,
        "login": paiement_login,
        "montant": montant,
        "name": name,
        "description": description,
        "return_url": return_url,
        "orderId": order_id,
        "callback_url": notify_url,
        # "cur": "eur"
    }

    # TODO url success
    resp = requests.post("https://ngsystem.net/sms/rest/smsService/stripe/pay",
                         data=json.dumps(data))
    if resp.status_code == 200:
        return resp.json()
    else:
        return False


def verifier_status(order_id):
    data = {
        "login": paiement_login,
        "password": paiement_password,
        "orderId": order_id
    }

    try:
        resp = requests.post("https://ngsystem.net/sms/rest/smsService/mobile/pay/status",
                             data=json.dumps(data))
        if resp.status_code == 200:
            return resp.json()
        else:
            return False
    except:
        return False


def get_solde():
    data = {
        "login": paiement_login,
        "password": paiement_password
    }

    try:
        resp = requests.post("https://ngsystem.net/sms/rest/smsService/mobile/pay/balance",
                             data=json.dumps(data))
        if resp.status_code == 200:
            return resp.json()
        else:
            return False
    except:
        return False
