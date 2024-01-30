import json
import os
import re
import secrets
import string
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.contrib import messages
from django.core import serializers
from django.core.paginator import Paginator
from django.core.mail import EmailMultiAlternatives, EmailMessage
from django.contrib.staticfiles import finders
from django.db import transaction
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from functools import lru_cache

from sequences import *
from .models import *

# Convert camel cased string to separated lowercase string
# Example: CamelCase -> camel case for capitalize_first=False
# Example: CamelCase -> Camel case for capitalize_first=True
def camel_case_to_separated_lower(string, capitalize_first=False):
    if capitalize_first:
        return camel_case_to_separated_lower(string).capitalize()
    else:
        return re.sub('([A-Z][a-z]+)', r' \1', re.sub('([A-Z]+)', r' \1', string)).lower().strip()

# Generate random password that meets password requirements
def generate_password():
    alphabet = string.ascii_letters + string.digits + string.punctuation
    while True:
        password = ''.join(secrets.choice(alphabet) for i in range(10))
        if (any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)
                and any(c in string.punctuation for c in password)):
            return password

# Add, Edit, Delete entities
# Pass None for success_message_identifier if no message wanted to be shown after success
def AddEntity(request, model, success_message_identifier, **kwargs):
    try:
        with transaction.atomic():
            if model == User:
                new_entry = User.objects.create_user(**kwargs)
            else:
                new_entry = model(**kwargs)
                new_entry.save()

            if success_message_identifier:
                model_name = camel_case_to_separated_lower(model.__name__)
                messages.success(request, "New " + model_name + " " + success_message_identifier + " created successfully!")
            return new_entry
    except Exception as e:
        messages.error(request, "Error occurred with the message " + str(e))

def EditEntity(request, model, entity_id, success_message_identifier, **kwargs):
    try:
        with transaction.atomic():
            to_edit = model.objects.get(id=entity_id)
            for key, value in kwargs.items():
                if hasattr(to_edit, key):
                    setattr(to_edit, key, value)
                else:
                    raise AttributeError(f"'{to_edit.__class__.__name__}' object has no attribute '{key}'")
            to_edit.save()
            if success_message_identifier:
                model_name = camel_case_to_separated_lower(model.__name__, True)
                messages.success(request, model_name + " " + success_message_identifier + " edited successfully!")
    except Exception as e:
        messages.error(request, "Error occurred with the message " + str(e))

def DeleteEntity(request, model, entity_id, success_message_identifier, **kwargs):
    try:
        with transaction.atomic():
            to_delete = model.objects.get(id=entity_id)
            to_delete.delete()
            if success_message_identifier:
                model_name = camel_case_to_separated_lower(model.__name__, True)
                messages.success(request, model_name + " " + success_message_identifier + " deleted successfully!")
    except Exception as e:
        messages.error(request, "Error occurred with the message " + str(e))

# Serializer
def serialize_and_paginate(queryset, page_size=10, paginate=True, one=False, extra_fields=None):
    if one:
        serialized_data = json.loads(serializers.serialize('json', [queryset]))
        serialized_data[0]['fields'].update({
            'id': serialized_data[0]['pk'],
            **(extra_fields(queryset) if extra_fields else {})
        })
        return serialized_data[0]['fields']
    serialized_data = []
    for obj in queryset:
        serialized_obj = json.loads(serializers.serialize('json', [obj]))
        serialized_obj[0]['fields'].update({
            'id': serialized_obj[0]['pk'],
            **(extra_fields(obj) if extra_fields else {})
        })
        serialized_data.append(serialized_obj[0]['fields'])

    if paginate:
        paginator = Paginator(serialized_data, page_size)
        return paginator
    else:
        return serialized_data
    
# Get next value of sequences
def get_without_consume(sequence_name, prefix):
    next = prefix + str(get_last_value(sequence_name) + 1).zfill(settings.ZFILL)
    return next

def get_with_consume(sequence_name, prefix):
    next = prefix + str(get_next_value(sequence_name)).zfill(settings.ZFILL)
    return next

# Dropzone
def upload(request, dir):
    file = request.FILES.get('imageUpload')
    filename = file.name

    os.makedirs(os.path.join(settings.MEDIA_ROOT, dir), exist_ok=True)

    with open(os.path.join(settings.MEDIA_ROOT, dir, filename), 'wb+') as destination:
        for chunk in file.chunks():
            destination.write(chunk)

    return filename

def remove(dir, filename):
    if filename is None:
        path = os.path.join(settings.MEDIA_ROOT, dir)
    else:
        path = os.path.join(settings.MEDIA_ROOT, dir, filename)
    if os.path.exists(path):
        os.remove(path)
        return True
    else:
        return False

# Image data to attach to email
@lru_cache()
def image_data(image_path, header):
    with open(finders.find(image_path), 'rb') as f:
        image_data = f.read()
    image = MIMEImage(image_data)
    image.add_header('Content-ID', header)
    return image

# Send email
def send_email(data, html_template):
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('vcms/token.json'):
        creds = Credentials.from_authorized_user_file('vcms/token.json')
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired:
            try:
                creds.refresh(Request())
            except RefreshError:
                os.remove('vcms/token.json')
                creds = None

        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(
                'vcms/credentials.json', settings.SCOPES)
            creds = flow.run_local_server(port=8080)
        # Save the credentials for the next run
        with open('vcms/token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        # Call the Gmail API
        service = build('gmail', 'v1', credentials=creds)
        message = MIMEMultipart("alternative")
        message["Subject"] = data['email_subject']
        message["From"] = 'me'
        message["To"] = data['to_email']
        if 'cc_email' in data:
            message["Cc"] = data['cc_email']
        message.attach(MIMEText(data['email_body'], "plain"))
        message.attach(MIMEText(html_template, "html"))
        # message.attach(image_data('Logos/logo_with_text_below.png', '<logo>'))

        # Call the Gmail API to send the email
        message_as_bytes = base64.urlsafe_b64encode(message.as_bytes())
        message_as_base64 = message_as_bytes.decode()
        body = {'raw': message_as_base64}
        message = service.users().messages().send(userId='me', body=body).execute()

        return bool(message['id'])
    except Exception as e:
        return False
    
# Notification redirect
def redirect_view_appointment_staff(**kwargs):
    appointment_id = kwargs.get('appointment_id', None)
    staff_id = kwargs.get('staff_id', None)
    if appointment_id:
        return redirect('vcmsapp:view-appointment-staff', staff_id=staff_id, appointment_id=appointment_id)
    
def redirect_view_appointment_customer(**kwargs):
    appointment_id = kwargs.get('appointment_id', None)
    customer_id = kwargs.get('customer_id', None)
    if appointment_id:
        return redirect('vcmsapp:view-appointment-customer', customer_id=customer_id, appointment_id=appointment_id)
    
# Generate private key for customers
def generate_private_key():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pem