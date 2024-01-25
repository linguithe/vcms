from datetime import datetime
from django.conf import settings
from django.urls import reverse
from django.template.loader import render_to_string
from vcmsapp.models import *
from vcmsapp.utils import *

import logging

def send():
    try:
        emails = EmailQueue.objects.filter(
            is_sent=False,
            module='CustomerApprovedEmail',
            void=False
        )
        if emails:
            for email in emails:
                try:
                    if User.objects.filter(email=email.to).exists():
                        if User.objects.filter(email=email.to).count() <= 1:
                            email_to_send = emails.get(id=email.id)
                            if email_to_send.retry_count < settings.RETRY_LIMIT:
                                try:
                                    to = email_to_send.to
                                    to_user = User.objects.get(email=to)
                                    customer = Customer.objects.get(user=to_user)
                                    relative_url = reverse('vcmsapp:login')
                                    absolute_url = settings.HOST_ADDRESS + relative_url
                                    site = settings.HOST_ADDRESS

                                    context = {
                                        'customer': customer,
                                        'login_url': absolute_url,
                                    }
                                    html_template = render_to_string('email/CustomerApprovedEmail.html', context)

                                    data = {
                                        'email_body': '',
                                        'to_email': to,
                                        'email_subject': 'Your account has been approved!',
                                    }

                                    send_status = send_email(data, html_template)

                                    if send_status:
                                        email_to_send.is_sent = True
                                        email_to_send.send_datetime = datetime.now()
                                        email_to_send.save()
                                    else:
                                        email_to_send.retry_count += 1
                                        email_to_send.save()
                                except Exception as e:
                                    logging.error(str(e))
                            else:
                                email_to_send.void = True
                                email_to_send.save()
                        else:
                            f'Found multiple users binded to {email.to} in the system.'
                    else:
                        f'User {email.to} does not exist in the system.'
                except Exception as e:
                    logging.error(str(e))
    except Exception as e:
        logging.error(e)